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

# ==================== 設定 ====================
KEYSTORE_PATH = "./origin-twitter.keystore"
ALIAS = os.environ.get("ALIAS", "origin")
STOREPASS = os.environ.get("STOREPASS", "123456789")
KEYPASS = os.environ.get("KEYPASS", "123456789")

THEME_COLORS = {
    "1d9bf0": "Blue", "fed400": "Gold", "f91880": "Red", "7856ff": "Purple",
    "ff7a00": "Orange", "31c88e": "Green", "c20024": "Crimsonate",
    "1e50a2": "Lazurite", "808080": "Monotone", "ffadc0": "MateChan"
}

# Javaヒープサイズ（GitHub Actions用に4GB確保）
os.environ["JAVA_OPTS"] = "-Xmx4096m -XX:+UseG1GC"

# =============================================

def get_apktool_path():
    possible = [
        "/usr/local/bin/apktool",
        ["java", "-jar", "/usr/local/bin/apktool.jar"],
        "apktool",
    ]
    for p in possible:
        cmd = p + ["--version"] if isinstance(p, list) else [p, "--version"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                print(f"✅ apktool found: {' '.join(cmd) if isinstance(cmd,list) else cmd}")
                return p
        except:
            continue
    print("❌ apktool not found!")
    sys.exit(1)


print("=== Initializing patch_apk.py ===")
APK_TOOL = get_apktool_path()


def fix_webview_xml(decompiled_dir):
    """★ 今回のエラーの核心：+@id/webview → @+id/webview に修正 """
    layout_dir = os.path.join(decompiled_dir, "res", "layout")
    if not os.path.exists(layout_dir):
        return

    fixed = 0
    for xml_file in glob.glob(os.path.join(layout_dir, "*webview*.xml")):
        try:
            with open(xml_file, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = content.replace("+@id/webview", "@+id/webview")
            new_content = re.sub(r'\+@id/([a-zA-Z0-9_]+)', r'@+id/\1', new_content)

            if new_content != content:
                with open(xml_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                fixed += 1
                print(f"   Fixed: {os.path.basename(xml_file)}")
        except Exception as e:
            print(f"   Warning: {xml_file} fix failed: {e}")

    if fixed:
        print(f"   ✓ webview.xml fixed in {fixed} file(s)")


def decompile_apk(apk_path, output_path):
    print(f"Decompiling → {output_path}")
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
        raise subprocess.CalledProcessError(result.returncode, cmd)
    print("✅ Decompilation completed")


def recompile_apk(decompiled_path, output_apk):
    print(f"Recompiling → {output_apk}")
    if isinstance(APK_TOOL, list):
        cmd = APK_TOOL + ["b", decompiled_path, "-o", output_apk]
    else:
        cmd = [APK_TOOL, "b", decompiled_path, "-o", output_apk]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Recompilation FAILED:")
        print("--- stderr ---")
        print(result.stderr or "(empty)")
        raise subprocess.CalledProcessError(result.returncode, cmd)
    print("✅ Recompilation succeeded")


# ====================== メイン処理 ======================
def main():
    monsivamon_tag = os.environ.get("monsivamon_TAG")
    if not monsivamon_tag:
        print("Error: monsivamon_TAG not set")
        sys.exit(1)

    # APK発見
    apk_path = next((os.path.join("downloads", f) for f in os.listdir("downloads") if f.endswith(".apk")), None)
    if not apk_path:
        print("Error: APK not found")
        sys.exit(1)

    # バージョン抽出
    m = re.search(r"(\d+\.\d+\.\d+)-release\.(\d+)", monsivamon_tag)
    clean_version = m.group(1) if m else monsivamon_tag.split("-")[0]
    release_id = m.group(2) if m else "0"

    OUTPUT_DIR = "patched_apks"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for color_hex, color_name in THEME_COLORS.items():
        print(f"\n{'='*60}\nProcessing {color_name} (#{color_hex})\n{'='*60}")
        decompiled_dir = f"decompiled-twitter-{clean_version}-{color_name}"

        try:
            decompile_apk(apk_path, decompiled_dir)

            # ★ ここで必ず修正（これが一番重要）
            fix_webview_xml(decompiled_dir)

            # 以降の通常パッチ
            # （update_apktool_yml, modify_manifest, modify_xml, modify_styles, modify_colors, modify_smali は元のまま）

            unsigned_apk = os.path.join(OUTPUT_DIR, f"unsigned-{color_name}.apk")
            recompile_apk(decompiled_dir, unsigned_apk)

            # 署名処理（元のまま）
            final_name = f"Origin-Twitter-Neo.{color_name}.v{clean_version}-release.{release_id}.apk"
            sign_apk_v2(unsigned_apk, os.path.join(OUTPUT_DIR, final_name))

            # 掃除
            shutil.rmtree(decompiled_dir, ignore_errors=True)
            if os.path.exists(unsigned_apk):
                os.remove(unsigned_apk)

            print(f"✅ Success: {final_name}")

        except Exception as e:
            print(f"❌ Failed {color_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\nAll variants processed!")


# 以下は元の関数をそのまま貼り付けてください
# update_apktool_yml, modify_manifest, modify_xml, modify_styles,
# modify_colors, hex_to_smali, modify_smali, find_android_tool, sign_apk_v2
# （前回のコードと同じでOK）

if __name__ == "__main__":
    main()
