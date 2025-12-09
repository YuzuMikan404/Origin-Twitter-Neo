#!/usr/bin/env python3

import os
import subprocess
import yaml
import xml.etree.ElementTree as ET
import re
import sys
import shutil
import glob

KEYSTORE_PATH = "./origin-twitter.keystore"
ALIAS = "origin"
STOREPASS = "123456789"
KEYPASS = "123456789"

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
    """apktoolの実行パスを取得する"""
    possible_paths = [
        '/usr/local/bin/apktool',
        ['java', '-jar', '/usr/local/bin/apktool.jar'],
        'apktool'
    ]
    
    for path_spec in possible_paths:
        cmd = []
        if isinstance(path_spec, list):
            cmd = path_spec + ['--version']
        else:
            cmd = [path_spec, '--version']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
            if result.returncode == 0:
                print(f"✅ apktool found: {' '.join(cmd)}")
                return path_spec
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    print("❌ Error: Could not find a working apktool path")
    return None

print("=== Initializing patch_apk.py ===")
APK_TOOL = get_apktool_path()
if APK_TOOL is None:
    print("FATAL: apktool is not available.")
    sys.exit(1)
else:
    print(f"Using apktool command: {APK_TOOL}")

def main():
    # monsivamon_TAG を使用
    monsivamon_tag = os.getenv('monsivamon_TAG')
    
    if not monsivamon_tag or monsivamon_tag.lower() == 'null':
        print("Error: monsivamon_TAG is not set or null.")
        sys.exit(1)
    
    print(f"Original monsivamon_TAG: {monsivamon_tag}")
    
    # APKファイルの検索
    apk_path = None
    downloads_dir = "downloads"
    
    if os.path.exists(downloads_dir):
        for file in os.listdir(downloads_dir):
            if file.endswith(".apk"):
                apk_path = os.path.join(downloads_dir, file)
                break
    
    if not apk_path:
        print("Error: APK file not found in downloads directory.")
        if os.path.exists(downloads_dir):
            print("Files in downloads directory:")
            for file in os.listdir(downloads_dir):
                print(f"  - {file}")
        sys.exit(1)
    
    print(f"Found APK at: {apk_path}")
    
    # バージョン情報を抽出
    clean_version = monsivamon_tag.replace('-release', '')
    release_id = "0"  # 固定値
    
    print(f"Version: {clean_version}, Release ID: {release_id}")
    
    # 出力ディレクトリを作成
    OUTPUT_DIR = "patched_apks"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 各カラーバリエーションを処理
    for color_hex, color_name in THEME_COLORS.items():
        print(f"\n{'='*50}")
        print(f"Processing {color_name} theme (color: #{color_hex})")
        print(f"{'='*50}")
        
        # 各色用のデコンパイルディレクトリ
        decompiled_dir = f"decompiled-twitter-{clean_version}-{color_name}"
        
        try:
            # APKをデコンパイル
            decompile_apk(apk_path, decompiled_dir)
            
            # 修正を適用
            update_apktool_yml(decompiled_dir)
            modify_manifest(decompiled_dir)
            modify_xml(decompiled_dir)
            modify_styles(decompiled_dir, color_hex, color_name)
            modify_colors(decompiled_dir, color_hex)
            modify_smali(decompiled_dir, color_hex)
            
            # APKをリコンパイル
            unsigned_apk = os.path.join(OUTPUT_DIR, f"unsigned-{color_name}.apk")
            recompile_apk(decompiled_dir, unsigned_apk)
            
            # APKに署名
            final_apk_name = f"Origin-Twitter.{color_name}.v{clean_version}-release.{release_id}.apk"
            final_apk_path = os.path.join(OUTPUT_DIR, final_apk_name)
            sign_apk(unsigned_apk, final_apk_path)
            
            # 一時ファイルを削除
            if os.path.exists(unsigned_apk):
                os.remove(unsigned_apk)
            
            # デコンパイルディレクトリを削除
            shutil.rmtree(decompiled_dir, ignore_errors=True)
            
            print(f"✅ Successfully created: {final_apk_name}")
            
        except Exception as e:
            print(f"❌ Error processing {color_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 結果を表示
    print(f"\n{'='*50}")
    print("All color variants processed!")
    print(f"{'='*50}")
    
    apk_files = list(glob.glob(os.path.join(OUTPUT_DIR, "*.apk")))
    if apk_files:
        print(f"Generated {len(apk_files)} APK files:")
        for apk_file in sorted(apk_files):
            file_size = os.path.getsize(apk_file) / (1024 * 1024)  # MB単位
            print(f"  • {os.path.basename(apk_file)} ({file_size:.1f} MB)")
    else:
        print("No APK files were generated.")

def decompile_apk(apk_path, output_path):
    print(f"Decompiling APK to: {output_path}")
    
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    
    if isinstance(APK_TOOL, list):
        cmd = APK_TOOL + ["d", apk_path, "-o", output_path, "--force"]
    else:
        cmd = [APK_TOOL, "d", apk_path, "-o", output_path, "--force"]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"apktool decompile failed:")
        print(f"stderr: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)
    
    print("✅ Decompilation completed")

def update_apktool_yml(decompiled_path):
    yml_path = os.path.join(decompiled_path, "apktool.yml")
    if os.path.exists(yml_path):
        with open(yml_path, "r", encoding="utf-8") as f:
            yml_data = yaml.safe_load(f)
        doNotCompress = yml_data.get("doNotCompress", [])
        if ".so" not in doNotCompress:
            doNotCompress.append(".so")
        yml_data["doNotCompress"] = doNotCompress
        with open(yml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(yml_data, f)
        print("✅ Updated apktool.yml")

def modify_manifest(decompiled_path):
    manifest_path = os.path.join(decompiled_path, "AndroidManifest.xml")
    if not os.path.exists(manifest_path):
        return
    
    ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    application = root.find('application')
    if application is not None:
        application.set("{http://schemas.android.com/apk/res/android}extractNativeLibs", "true")
        tree.write(manifest_path, encoding="utf-8", xml_declaration=True)
        print("✅ Modified AndroidManifest.xml")

def modify_xml(decompiled_path):
    xml_files = [
        "res/layout/ocf_twitter_logo.xml",
        "res/layout/login_toolbar_seamful_custom_view.xml"
    ]
    
    for xml_file in xml_files:
        file_path = os.path.join(decompiled_path, xml_file)
        if not os.path.exists(file_path):
            continue
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # カラー置換
        content = content.replace("?dynamicColorGray1100", "@color/twitter_blue")
        content = content.replace("@color/gray_1100", "@color/twitter_blue")
        content = re.sub(r"#ff1d9bf0|#ff1da1f2", "@color/twitter_blue", content)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    print("✅ Modified XML files")

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
    print("✅ Modified styles.xml")

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
        "twitter_blue_opacity_58": f"#95{color_hex}"
    }
    
    for color_tag in root.findall("color"):
        name = color_tag.get("name", "")
        if name in opacity_map:
            color_tag.text = opacity_map[name]
    
    tree.write(colors_path, encoding="utf-8", xml_declaration=True)
    print("✅ Modified colors.xml")

def hex_to_smali(hex_color):
    int_color = int(hex_color, 16)
    smali_int = (int_color ^ 0xFFFFFF) + 1
    smali_value = f"-0x{smali_int:06x}"
    return smali_value.lower()

def modify_smali(decompiled_path, color_hex):
    smali_color = hex_to_smali(color_hex) + "00000000L"
    patterns = {
        re.compile(r"-0xe2641000000000L", re.IGNORECASE): smali_color,
        re.compile(r"0xff1d9bf0L", re.IGNORECASE): f"0xff{color_hex}L",
    }
    
    modified_count = 0
    for root_dir, _, files in os.walk(decompiled_path):
        for file in files:
            if file.endswith(".smali"):
                smali_path = os.path.join(root_dir, file)
                with open(smali_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                original_content = content
                for pattern, replacement in patterns.items():
                    content = pattern.sub(replacement, content)
                
                if content != original_content:
                    with open(smali_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    modified_count += 1
    
    print(f"✅ Modified {modified_count} .smali files")

def recompile_apk(decompiled_path, output_apk):
    print(f"Recompiling APK to: {output_apk}")
    
    if isinstance(APK_TOOL, list):
        cmd = APK_TOOL + ["b", decompiled_path, "-o", output_apk]
    else:
        cmd = [APK_TOOL, "b", decompiled_path, "-o", output_apk]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Recompilation failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)
    
    if os.path.exists(output_apk):
        file_size = os.path.getsize(output_apk) / (1024 * 1024)
        print(f"✅ Recompiled APK: {output_apk} ({file_size:.1f} MB)")
    else:
        raise FileNotFoundError(f"Recompiled APK not found: {output_apk}")

def sign_apk(unsigned_apk_path, signed_apk_path):
    print(f"Signing APK: {os.path.basename(unsigned_apk_path)}")
    
    # キーストアの確認
    if not os.path.exists(KEYSTORE_PATH):
        generate_keystore()
    
    # jarsignerで署名
    jarsigner_cmd = [
        "jarsigner", "-verbose",
        "-sigalg", "SHA1withRSA",
        "-digestalg", "SHA1",
        "-keystore", KEYSTORE_PATH,
        "-storepass", STOREPASS,
        "-keypass", KEYPASS,
        unsigned_apk_path,
        ALIAS
    ]
    
    result = subprocess.run(jarsigner_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"jarsigner failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, jarsigner_cmd)
    
    # zipalignで最適化
    zipalign_path = find_zipalign()
    if zipalign_path:
        align_cmd = [zipalign_path, "-v", "4", unsigned_apk_path, signed_apk_path]
        result = subprocess.run(align_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"zipalign failed: {result.stderr}")
            # 署名だけは成功しているので、署名済みAPKをそのまま使用
            shutil.copy(unsigned_apk_path, signed_apk_path)
    else:
        shutil.copy(unsigned_apk_path, signed_apk_path)
    
    print(f"✅ Signed APK: {os.path.basename(signed_apk_path)}")

def generate_keystore():
    print("Generating keystore...")
    
    cmd = [
        "keytool", "-genkey", "-v",
        "-keystore", KEYSTORE_PATH,
        "-alias", ALIAS,
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-storepass", STOREPASS,
        "-keypass", KEYPASS,
        "-dname", "CN=OriginTwitter, OU=Development, O=YuzuMikan404, L=Tokyo, C=JP"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, input="\n")
    if result.returncode != 0:
        print(f"keytool failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)
    
    print("✅ Keystore generated")

def find_zipalign():
    android_home = os.environ.get("ANDROID_HOME")
    if not android_home:
        return None
    
    build_tools_dir = os.path.join(android_home, "build-tools")
    if not os.path.exists(build_tools_dir):
        return None
    
    versions = sorted(os.listdir(build_tools_dir), reverse=True)
    for version in versions:
        zipalign_path = os.path.join(build_tools_dir, version, "zipalign")
        if os.path.exists(zipalign_path):
            return zipalign_path
    
    return None

if __name__ == "__main__":
    main()
