#!/usr/bin/env python3

import os
import subprocess
import yaml
import xml.etree.ElementTree as ET
import re
import sys

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

APK_TOOL = "apktool"
APK_VERSION = ""

def main():
    # monsivamon_TAG を使用
    monsivamon_tag = os.getenv('monsivamon_TAG')
    
    if not monsivamon_tag or monsivamon_tag.lower() == 'null':
        print("Error: monsivamon_TAG is not set or null.")
        sys.exit(1)
    
    print(f"Original monsivamon_TAG: {monsivamon_tag}")
    
    # 複数の可能性のあるAPKファイル名を試す
    possible_filenames = [
        f"twitter-piko-v{monsivamon_tag}.apk",  # ワークフローがダウンロードするファイル名
        f"twitter-piko-v{monsivamon_tag.replace('-release', '')}.apk",  # 元の想定ファイル名
        f"twitter-piko-{monsivamon_tag}.apk",  # 別の可能性
    ]
    
    apk_path = None
    for filename in possible_filenames:
        test_path = f"downloads/{filename}"
        print(f"Checking for APK at: {test_path}")
        if os.path.exists(test_path):
            apk_path = test_path
            break
    
    if not apk_path:
        print("Error: APK file not found. Tried the following patterns:")
        for filename in possible_filenames:
            print(f"  - downloads/{filename}")
        
        # ダウンロードディレクトリの内容を表示
        if os.path.exists("downloads"):
            print("\nFiles in downloads directory:")
            for file in os.listdir("downloads"):
                print(f"  - {file}")
        else:
            print("downloads directory does not exist.")
        
        sys.exit(1)
    
    print(f"Found APK at: {apk_path}")
    
    # バージョン情報を抽出（表示用）
    clean_version = monsivamon_tag.replace('-release', '')
    
    # デコンパイル用のディレクトリを作成
    output_path = f"decompiled-twitter-{clean_version}"
    
    # APKをデコンパイル
    try:
        decompile_apk(apk_path, output_path)
    except Exception as e:
        print(f"Error decompiling APK: {e}")
        sys.exit(1)
    
    # apktool.ymlを更新
    try:
        update_apktool_yml(output_path)
    except Exception as e:
        print(f"Error updating apktool.yml: {e}")
    
    # AndroidManifest.xmlを修正
    try:
        modify_manifest(output_path)
    except Exception as e:
        print(f"Error modifying manifest: {e}")
    
    # XMLファイルを修正
    try:
        modify_xml(output_path)
    except Exception as e:
        print(f"Error modifying XML files: {e}")
    
    print(f"Decompilation and modifications completed successfully in {output_path}")

def decompile_apk(apk_path, output_path):
    print(f"Checking if APK file exists: {apk_path}")
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK file not found: {apk_path}")
    subprocess.run([APK_TOOL, "d", apk_path, "-o", output_path, "--force"], check=True)

def update_apktool_yml(decompiled_path):
    """
    Update apktool.yml so that .so files are not recompressed
    """
    yml_path = os.path.join(decompiled_path, "apktool.yml")
    if os.path.exists(yml_path):
        print(f"Updating doNotCompress in {yml_path}")
        with open(yml_path, "r", encoding="utf-8") as f:
            yml_data = yaml.safe_load(f)
        doNotCompress = yml_data.get("doNotCompress", [])
        if ".so" not in doNotCompress and "so" not in doNotCompress:
            doNotCompress.append(".so")
        yml_data["doNotCompress"] = doNotCompress
        with open(yml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(yml_data, f)
    else:
        print(f"{yml_path} not found. Skipping update for doNotCompress.")

def modify_manifest(decompiled_path):
    """
    Change the android:extractNativeLibs attribute of the <application> tag in AndroidManifest.xml to true
    """
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
        print("Modified AndroidManifest.xml: set android:extractNativeLibs to true")

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
        content = content.replace("?dynamicColorGray1100", "@color/twitter_blue")
        content = content.replace("@color/gray_1100", "@color/twitter_blue")
        content = re.sub(r"#ff1d9bf0|#ff1da1f2", "@color/twitter_blue", content)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Modified {xml_file}")

if __name__ == "__main__":
    main()
