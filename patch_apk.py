#!/usr/bin/env python3

import os
import subprocess
import yaml
import xml.etree.ElementTree as ET
import re

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

# apktoolのパス（環境に合わせて修正してください）
APK_TOOL = "apktool"
APK_VERSION = ""

# Obtaining the version from GitHub environment variables
apk_version = os.getenv('YuzuMikan404_TAG')  
apk_file_name = f"twitter-piko-v{apk_version}.apk" 
apk_path = f"downloads/{apk_file_name}"  

print(f"APK Path: {apk_path}")

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

def get_apk_version(apk_path):
    global APK_VERSION
    match = re.search(r"twitter-piko-v(\d+\.\d+\.\d+)", apk_path)
    if match:
        APK_VERSION = match.group(1)
    else:
        APK_VERSION = "unknown"
    print(f"Detected APK Version: {APK_VERSION}")

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
            f.write(content)  # 修正：write文を追加
        print(f"Modified {xml_file}")

# メイン処理を追加（必要に応じて）
if __name__ == "__main__":
    # 必要な処理をここに追加
    pass
