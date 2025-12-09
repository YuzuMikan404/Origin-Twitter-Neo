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

# apktoolのパスを環境に合わせて設定
APK_TOOL = "apktool"  # パスが通っていることを期待
APK_VERSION = ""

def check_apktool():
    """apktoolが利用可能かチェックする"""
    try:
        result = subprocess.run([APK_TOOL, "--version"], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"apktool found: {result.stdout.strip()}")
            return True
        else:
            print(f"apktool check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error checking apktool: {e}")
        return False

def main():
    # apktoolのチェック
    if not check_apktool():
        print("Error: apktool is not available. Please install it first.")
        sys.exit(1)
    
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
    
    # 既にディレクトリが存在する場合は削除
    if os.path.exists(output_path):
        print(f"Removing existing directory: {output_path}")
        import shutil
        shutil.rmtree(output_path)
    
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
    
    print(f"Decompiling APK to: {output_path}")
    result = subprocess.run([APK_TOOL, "d", apk_path, "-o", output_path, "--force"], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"apktool decompile failed with error:")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args)
    
    print("Decompilation completed successfully")

# ... 他の関数は同じ ...
