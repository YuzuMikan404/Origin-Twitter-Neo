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
    # Obtaining the version from GitHub environment variables
    # YuzuMikan404_TAG が null の場合は monsivamon_TAG を使用
    apk_version = os.getenv('YuzuMikan404_TAG')
    if not apk_version or apk_version.lower() == 'null':
        print("Warning: YuzuMikan404_TAG is null or not set. Using monsivamon_TAG instead.")
        apk_version = os.getenv('monsivamon_TAG')
    
    if not apk_version or apk_version.lower() == 'null':
        print("Error: Both YuzuMikan404_TAG and monsivamon_TAG are not set or null.")
        sys.exit(1)
    
    # バージョンから "release" サフィックスを削除
    apk_version = apk_version.replace('-release', '')
    
    apk_file_name = f"twitter-piko-v{apk_version}.apk"
    apk_path = f"downloads/{apk_file_name}"
    
    print(f"APK Version: {apk_version}")
    print(f"APK File Name: {apk_file_name}")
    print(f"APK Path: {apk_path}")
    
    # ファイルが存在するか確認
    if not os.path.exists(apk_path):
        print(f"Error: APK file not found at {apk_path}")
        print("Please make sure the APK has been downloaded to the downloads/ directory.")
        sys.exit(1)
    
    # デコンパイル用のディレクトリを作成
    output_path = f"decompiled-twitter-{apk_version}"
    
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
