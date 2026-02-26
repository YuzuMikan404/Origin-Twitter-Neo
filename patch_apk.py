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
import traceback

# 環境変数から設定を読み込む（GitHub Actions Secrets）
KEYSTORE_PATH = "./origin-twitter.keystore"
ALIAS = os.environ.get("ALIAS", "origin")
STOREPASS = os.environ.get("STOREPASS", "123456789")
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
    """apktool の実行パスを検出"""
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
    """すべての layout XML で +@id/ を @+id/ に置換（webview.xml エラー対策）"""
    layout_dir = os.path.join(decompiled_dir, "res", "layout")
    if not os.path.exists(layout_dir):
        print(f"  No layout directory found in {decompiled_dir}")
        return

    fixed_count = 0
    for xml_path in glob.glob(os.path.join(layout_dir, "*.xml")):
        try:
            with open(xml_path, "r", encoding="utf-8") as f:
                content = f.read()

            original = content
            # 問題の代表例を優先修正
            content = content.replace("+@id/webview", "@+id/webview")
            # 他の +@id/xxx もすべて修正
            content = re.sub(r'\+@id/([a-zA-Z0-9_]+)', r'@+id/\1', content)

            if content != original:
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(content)
                fixed_count += 1
                print(f"  Fixed ID reference in: {os.path.basename(xml_path)}")

        except Exception as e:
            print(f"  Warning: Failed to fix {xml_path}: {e}")

    if fixed_count > 0:
        print(f"  ✓ Fixed {fixed_count} layout XML file(s)")
    else:
        print("  No +@id/ references needed fixing")


def main():
    monsivamon_tag = os.environ.get("monsivamon_TAG")
    if not monsivamon_tag or monsivamon_tag.lower() in ("null", "none", ""):
        print("Error: monsivamon_TAG is not set or invalid.")
        sys.exit(1)

    print(f"Original monsivamon_TAG: {monsivamon_tag}")

    # APK ファイルを探す
    apk_path = None
    downloads_dir = "downloads"
    if os.path.isdir(downloads_dir):
        for filename in os.listdir(downloads_dir):
            if filename.lower().endswith(".apk"):
                apk_path = os.path.join(downloads_dir, filename)
                break

    if not apk_path or not os.path.isfile(apk_path):
        print(f"Error: No APK file found in {downloads_dir}/")
        sys.exit(1)

    print(f"Found APK: {apk_path}")

    # バージョン解析
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

    if not os.path.exists(KEYSTORE_PATH):
        print(f"❌ Keystore not found: {KEYSTORE_PATH}")
        sys.exit(1)

    for color_hex, color_name in THEME_COLORS.items():
        print("\n" + "=" * 70)
        print(f"Processing {color_name} theme (color: #{color_hex})")
        print("=" * 70)

        decompiled_dir = f"decompiled-twitter-{clean_version}-{color_name}"

        try:
            # デコンパイル
            decompile_apk(apk_path, decompiled_dir)

            # ★ ここで ID参照問題を即座に修正（これが最重要）
            fix_webview_xml(decompiled_dir)

            # パッチ適用
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

            # クリーンアップ
            if os.path.exists(unsigned_apk):
                os.remove(unsigned_apk)
            shutil.rmtree(decompiled_dir, ignore_errors=True)

            print(f"✅ Successfully created: {final_apk_name}")

        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed for {color_name}:")
            print(f"  Command: {' '.join(e.cmd)}")
            print(f"  Return code: {e.returncode}")
            if e.stderr:
                print("  stderr:\n" + e.stderr.strip())
            if e.stdout:
                print("  stdout:\n" + e.stdout.strip())
            continue
        except Exception as e:
            print(f"❌ Error processing {color_name}: {e}")
            traceback.print_exc()
            continue

    print("\n" + "=" * 70)
    print("All color variants processed!")


def decompile_apk(apk_path, output_path):
    print(f"Decompiling to: {output_path}")
    if os.path.exists(output_path):
        shutil.rmtree(output_path, ignore_errors=True)

    cmd = (
        APK_TOOL + ["d", "-f", apk_path, "-o", output_path]
        if isinstance(APK_TOOL, list)
        else [APK_TOOL, "d", "-f", apk_path, "-o", output_path]
    )

    env = os.environ.copy()
    env["JAVA_OPTS"] = env.get("JAVA_OPTS", "-Xmx6g")  # OOM対策

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print("Decompile failed:")
        print("stderr:\n" + result.stderr.strip())
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    print("✅ Decompilation completed")


def recompile_apk(decompiled_path, output_apk):
    print(f"Recompiling to: {output_apk}")
    cmd = (
        APK_TOOL + ["b", decompiled_path, "-o", output_apk]
        if isinstance(APK_TOOL, list)
        else [APK_TOOL, "b", decompiled_path, "-o", output_apk]
    )

    print(f"Running: {' '.join(cmd)}")

    env = os.environ.copy()
    env["JAVA_OPTS"] = env.get("JAVA_OPTS", "-Xmx6g")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print("Recompilation failed:")
        print("stderr:\n" + (result.stderr.strip() or "(empty)"))
        print("stdout:\n" + (result.stdout.strip() or "(empty)"))
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    print("✅ Recompilation succeeded")


# 以下は変更なしの既存関数（省略形）
def update_apktool_yml(decompiled_path):
    yml_path = os.path.join(decompiled_path, "apktool.yml")
    if not os.path.exists(yml_path):
        return
    with open(yml_path, "r", encoding="utf-8") as f:
        yml_data = yaml.safe_load(f) or {}
    doNotCompress = yml_data.get("doNotCompress", [])
    if ".so" not in doNotCompress:
        doNotCompress.append(".so")
    yml_data["doNotCompress"] = doNotCompress
    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(yml_data, f)


def modify_manifest(decompiled_path):
    manifest_path = os.path.join(decompiled_path, "AndroidManifest.xml")
    if not os.path.exists(manifest_path):
        return
    ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    application = root.find(".//application")
    if application is not None:
        application.set("{http://schemas.android.com/apk/res/android}extractNativeLibs", "true")
    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)


def modify_xml(decompiled_path):
    xml_files = [
        "res/layout/ocf_twitter_logo.xml",
        "res/layout/login_toolbar_seamful_custom_view.xml",
    ]
    for xml_file in xml_files:
        file_path = os.path.join(decompiled_path, xml_file)
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("?dynamicColorGray1100", "@color/twitter_blue")
        content = content.replace("@color/gray_1100", "@color/twitter_blue")
        content = re.sub(r"#ff1d9bf0|#ff1da1f2", "@color/twitter_blue", content, flags=re.IGNORECASE)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


def modify_styles(decompiled_path, color_hex, color_name):
    styles_path = os.path.join(decompiled_path, "res/values/styles.xml")
    if not os.path.exists(styles_path):
        return
    tree = ET.parse(styles_path)
    root = tree.getroot()
    for style in root.findall("style"):
        name = style.get("name", "")
        if name in ["TwitterBase.Dim", "TwitterBase.LightsOut", "TwitterBase.Standard"]:
            for item in style.findall("item"):
                if item.get("name") == "coreColorBadgeVerified":
                    item.text = "@color/blue_500"
        elif name in ["PaletteDim", "PaletteLightsOut", "PaletteStandard"]:
            for item in style.findall("item"):
                if item.get("name") == "abstractColorUnread":
                    item.text = "@color/twitter_blue_opacity_50"
                elif item.get("name") == "abstractColorLink" and name == "PaletteStandard":
                    item.text = "@color/twitter_blue"
        elif name in ["Theme.LaunchScreen"]:
            for item in style.findall("item"):
                if item.get("name") == "windowSplashScreenBackground":
                    item.text = "@color/twitter_blue"
    tree.write(styles_path, encoding="utf-8", xml_declaration=True)


def modify_colors(decompiled_path, color_hex):
    colors_path = os.path.join(decompiled_path, "res/values/colors.xml")
    if not os.path.exists(colors_path):
        return
    tree = ET.parse(colors_path)
    root = tree.getroot()
    hex_color = f"#ff{color_hex}"
    opacity_map = {
        "twitter_blue": hex_color,
        "deep_transparent_twitter_blue": f"#cc{color_hex}",
        "twitter_blue_opacity_30": f"#4d{color_hex}",
        "twitter_blue_opacity_50": f"#80{color_hex}",
        "twitter_blue_opacity_58": f"#95{color_hex}",
    }
    for color_tag in root.findall("color"):
        name = color_tag.get("name", "")
        if name in opacity_map:
            color_tag.text = opacity_map[name]
    tree.write(colors_path, encoding="utf-8", xml_declaration=True)


def hex_to_smali(hex_color):
    int_color = int(hex_color, 16)
    smali_int = (int_color ^ 0xFFFFFF) + 1
    return f"-0x{smali_int:06x}".lower()


def modify_smali(decompiled_path, color_hex):
    smali_color = hex_to_smali(color_hex) + "00000000L"
    patterns = {
        re.compile(r"-0xe2641000000000L", re.IGNORECASE): smali_color,
        re.compile(r"0xff1d9bf0L", re.IGNORECASE): f"0xff{color_hex}L",
    }
    for root_dir, _, files in os.walk(decompiled_path):
        for file in files:
            if not file.endswith(".smali"):
                continue
            smali_path = os.path.join(root_dir, file)
            try:
                with open(smali_path, "r", encoding="utf-8") as f:
                    content = f.read()
                original = content
                for pattern, replacement in patterns.items():
                    content = pattern.sub(replacement, content)
                if content != original:
                    with open(smali_path, "w", encoding="utf-8") as f:
                        f.write(content)
            except Exception:
                continue


def find_android_tool(tool_name):
    android_home = os.environ.get("ANDROID_HOME")
    if not android_home:
        return tool_name
    build_tools_dir = os.path.join(android_home, "build-tools")
    if not os.path.exists(build_tools_dir):
        return tool_name
    versions = sorted(os.listdir(build_tools_dir), reverse=True)
    for version in versions:
        tool_path = os.path.join(build_tools_dir, version, tool_name)
        if os.path.exists(tool_path):
            return tool_path
    return tool_name


def sign_apk_v2(unsigned_apk_path, signed_apk_path):
    print(f"Signing: {os.path.basename(unsigned_apk_path)}")

    aligned_apk = unsigned_apk_path + ".aligned"
    zipalign_tool = find_android_tool("zipalign")

    align_cmd = [zipalign_tool, "-f", "-v", "4", unsigned_apk_path, aligned_apk]
    try:
        subprocess.run(align_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"zipalign failed: {e.stderr}")
        shutil.copy(unsigned_apk_path, aligned_apk)

    apksigner_tool = find_android_tool("apksigner")
    sign_cmd = [
        apksigner_tool, "sign",
        "--ks", KEYSTORE_PATH,
        "--ks-pass", f"pass:{STOREPASS}",
        "--ks-key-alias", ALIAS,
        "--key-pass", f"pass:{KEYPASS}",
        "--out", signed_apk_path,
        aligned_apk
    ]

    result = subprocess.run(sign_cmd, capture_output=True, text=True)
    if os.path.exists(aligned_apk):
        try:
            os.remove(aligned_apk)
        except OSError:
            pass

    if result.returncode != 0:
        print(f"apksigner failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, sign_cmd, result.stdout, result.stderr)

    print(f"✅ Signed: {os.path.basename(signed_apk_path)}")


if __name__ == "__main__":
    main()
