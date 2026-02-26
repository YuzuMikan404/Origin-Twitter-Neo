#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import yaml
import xml.etree.ElementTree as ET
import re
import sys
import shutil
import glob

# 環境変数から設定を読み込む（GitHub Actionsで設定したSecretsがここに入る）
KEYSTORE_PATH = "./origin-twitter.keystore"
ALIAS = os.environ.get("ALIAS", "origin")
STOREPASS = os.environ.get("STOREPASS", "123456789")  # デフォルト値はローカルテスト用
KEYPASS = os.environ.get("KEYPASS", "123456789")

THEME_COLORS = {
    "1d9bf0": "Blue",
    "fed400": "Gold",
    "f91880": "Red",
    "7856ff": "Purple",
    "ff7a00": "Orange",
    "31c88e": "Green",
    "c20024": "Crimsonate",
    "1e50a2": "Lazurite",
    "808080": "Monotone",
    "ffadc0": "MateChan"
}


def get_apktool_path():
    """apktoolの実行パスを取得する。"""
    possible_paths = [
        "/usr/local/bin/apktool",
        ["java", "-jar", "/usr/local/bin/apktool.jar"],
        "apktool",
    ]

    for path_spec in possible_paths:
        if isinstance(path_spec, list):
            cmd = path_spec + ["--version"]
        else:
            cmd = [path_spec, "--version"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode == 0:
                print(f"✅ apktool found: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
                return path_spec
        except Exception as e:
            print(f"Warning: checking {cmd} raised {e!r}")
            continue

    print("❌ Error: Could not find a working apktool path")
    return None


print("=== Initializing patch_apk.py ===")
APK_TOOL = get_apktool_path()
if APK_TOOL is None:
    print("FATAL: apktool is not available.")
    sys.exit(1)


def fix_webview_xml(decompiled_dir):
    """webview.xml 内の古いID参照 (+@id/) を現代的な形式 (@+id/) に修正"""
    layout_dir = os.path.join(decompiled_dir, "res", "layout")
    if not os.path.exists(layout_dir):
        print(f"  No layout directory found in {decompiled_dir}")
        return

    fixed_count = 0
    for xml_path in glob.glob(os.path.join(layout_dir, "*.xml")):
        if "webview" not in os.path.basename(xml_path).lower():
            continue

        try:
            with open(xml_path, "r", encoding="utf-8") as f:
                content = f.read()

            original = content
            # 最も問題になりやすい箇所を優先的に置換
            content = content.replace('+@id/webview', '@+id/webview')
            # 念のため他の +@id/ も修正
            content = re.sub(r'\+@id/([a-zA-Z0-9_]+)', r'@+id/\1', content)

            if content != original:
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(content)
                fixed_count += 1
                print(f"  Fixed ID reference in: {os.path.basename(xml_path)}")

        except Exception as e:
            print(f"  Warning: Failed to process {xml_path}: {e}")

    if fixed_count > 0:
        print(f"  ✓ Fixed {fixed_count} webview.xml file(s)")
    else:
        print("  No webview.xml needed fixing")


def main():
    monsivamon_tag = os.environ.get("monsivamon_TAG")
    if not monsivamon_tag or monsivamon_tag.lower() in ("null", "none"):
        print("Error: monsivamon_TAG is not set or null.")
        sys.exit(1)

    print(f"Original monsivamon_TAG: {monsivamon_tag}")

    # APKファイルのパスを特定
    apk_path = None
    downloads_dir = "downloads"

    if os.path.exists(downloads_dir) and os.path.isdir(downloads_dir):
        for filename in os.listdir(downloads_dir):
            if filename.endswith(".apk"):
                apk_path = os.path.join(downloads_dir, filename)
                break

    if not apk_path or not os.path.isfile(apk_path):
        print(f"Error: APK file not found in {downloads_dir}/")
        sys.exit(1)

    print(f"Found APK at: {apk_path}")

    # バージョン抽出
    version_pattern = r"(\d+\.\d+\.\d+)-release\.(\d+)"
    match = re.search(version_pattern, monsivamon_tag)
    if match:
        clean_version = match.group(1)
        release_id = match.group(2)
    else:
        clean_version = monsivamon_tag.split("-release")[0].split("-")[0]
        release_id = "0"

    print(f"Clean version: {clean_version}, Release ID: {release_id}")

    OUTPUT_DIR = "patched_apks"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # キーストアの存在確認
    if not os.path.exists(KEYSTORE_PATH):
        print(f"❌ Error: Keystore file not found at {KEYSTORE_PATH}")
        sys.exit(1)

    for color_hex, color_name in THEME_COLORS.items():
        print("\n" + "=" * 60)
        print(f"Processing {color_name} theme (color: #{color_hex})")
        print("=" * 60)

        decompiled_dir = f"decompiled-twitter-{clean_version}-{color_name}"

        try:
            # 1. デコンパイル
            decompile_apk(apk_path, decompiled_dir)

            # ★ ここで webview.xml の問題を修正（これが今回のエラー対策の核心）
            fix_webview_xml(decompiled_dir)

            # 以降の通常パッチ処理
            update_apktool_yml(decompiled_dir)
            modify_manifest(decompiled_dir)
            modify_xml(decompiled_dir)
            modify_styles(decompiled_dir, color_hex, color_name)
            modify_colors(decompiled_dir, color_hex)
            modify_smali(decompiled_dir, color_hex)

            # リコンパイル
            unsigned_apk = os.path.join(OUTPUT_DIR, f"unsigned-{color_name}.apk")
            recompile_apk(decompiled_dir, unsigned_apk)

            # 署名
            final_apk_name = f"Origin-Twitter-Neo.{color_name}.v{clean_version}-release.{release_id}.apk"
            final_apk_path = os.path.join(OUTPUT_DIR, final_apk_name)
            sign_apk_v2(unsigned_apk, final_apk_path)

            # 掃除
            if os.path.exists(unsigned_apk):
                os.remove(unsigned_apk)
            shutil.rmtree(decompiled_dir, ignore_errors=True)

            print(f"✅ Successfully created: {final_apk_name}")

        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed for {color_name}:")
            print(f"  Command: {' '.join(e.cmd)}")
            print(f"  Return code: {e.returncode}")
            if e.stderr:
                print("  stderr:")
                print(e.stderr.strip())
            continue
        except Exception as e:
            print(f"❌ Unexpected error processing {color_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "=" * 60)
    print("All color variants processed!")


# 以下は既存の関数（変更なしまたは軽微な改善のみ）

def decompile_apk(apk_path, output_path):
    print(f"Decompiling APK to: {output_path}")
    if os.path.exists(output_path):
        shutil.rmtree(output_path, ignore_errors=True)

    if isinstance(APK_TOOL, list):
        cmd = APK_TOOL + ["d", "-f", apk_path, "-o", output_path]
    else:
        cmd = [APK_TOOL, "d", "-f", apk_path, "-o", output_path]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Decompile failed:")
        print(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    print("✅ Decompilation completed")


def recompile_apk(decompiled_path, output_apk):
    print(f"Recompiling APK to: {output_apk}")

    if isinstance(APK_TOOL, list):
        cmd = APK_TOOL + ["b", decompiled_path, "-o", output_apk]
    else:
        cmd = [APK_TOOL, "b", decompiled_path, "-o", output_apk]

    # ログをより詳細に出力
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Recompilation failed:")
        print("stderr:")
        print(result.stderr.strip() or "(empty)")
        print("stdout:")
        print(result.stdout.strip() or "(empty)")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

    print("✅ Recompilation succeeded")


# 他の関数（modify_xxx, sign_apk_v2 など）は変更なしなので省略
# （必要ならそのままコピーしてください）

def update_apktool_yml(decompiled_path): ...  # 元のまま
def modify_manifest(decompiled_path): ...     # 元のまま
def modify_xml(decompiled_path): ...          # 元のまま
def modify_styles(decompiled_path, color_hex, color_name): ...  # 元のまま
def modify_colors(decompiled_path, color_hex): ...              # 元のまま
def hex_to_smali(hex_color): ...              # 元のまま
def modify_smali(decompiled_path, color_hex): ...  # 元のまま
def find_android_tool(tool_name): ...         # 元のまま
def sign_apk_v2(unsigned_apk_path, signed_apk_path): ...  # 元のまま


if __name__ == "__main__":
    main()
