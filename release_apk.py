#!/usr/bin/env python3

import os
import re
import requests
import sys

GITHUB_REPO = "YuzuMikan404/Origin-Twitter" 
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") 
if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN environment variable is not set.")
    sys.exit(1)

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
APK_DIR = "patched_apks"
DOWNLOAD_DIR = "downloads"

# 1. Get version and release ID from downloaded APK
def extract_version_and_release_id():
    print(f"Looking for APK files in {DOWNLOAD_DIR}...")
    
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Error: Directory {DOWNLOAD_DIR} does not exist.")
        return None, None
    
    for apk_name in os.listdir(DOWNLOAD_DIR):
        print(f"Found file: {apk_name}")
        
        # 複数のファイル名パターンを試す
        patterns = [
            r"twitter-piko-v?(\d+\.\d+\.\d+)-release\.(\d+)\.apk",  # twitter-piko-v11.46.0-release.0.apk
            r"twitter-piko-v?(\d+\.\d+\.\d+)\.apk",  # twitter-piko-v11.46.0.apk
            r"twitter-piko-(\d+\.\d+\.\d+)-release\.(\d+)\.apk",  # twitter-piko-11.46.0-release.0.apk
        ]
        
        for pattern in patterns:
            match = re.search(pattern, apk_name)
            if match:
                if len(match.groups()) == 2:
                    version, release_id = match.groups()
                else:
                    version = match.group(1)
                    release_id = "0"  # デフォルトのリリースID
                
                print(f"Detected APK Version: {version}, Release ID: {release_id}")
                return version, release_id
    
    print("Error: Unable to extract version and release ID.")
    return None, None

# 2. Create a new release on GitHub
def create_github_release(version, release_id):
    tag_name = f"{version}-release.{release_id}"
    print(f"Creating GitHub release with tag: {tag_name}")
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # まず、既存のリリースがあるかチェック
    response = requests.get(GITHUB_API, headers=headers)
    if response.status_code == 200:
        releases = response.json()
        for release in releases:
            if release.get("tag_name") == tag_name:
                print(f"Release {tag_name} already exists. Using existing release.")
                return release["id"], release["upload_url"].split("{")[0]
    
    # 新規リリースを作成
    data = {
        "tag_name": tag_name,
        "name": f"Origin Twitter v{version}-release.{release_id}",
        "body": f"Auto-generated release: Origin Twitter version {version}-release.{release_id}.",
        "draft": False,
        "prerelease": False
    }
    
    response = requests.post(GITHUB_API, json=data, headers=headers)
    print(f"Create release response status: {response.status_code}")
    
    if response.status_code == 201:
        release_info = response.json()
        print(f"GitHub Release created: {release_info['html_url']}")
        return release_info["id"], release_info["upload_url"].split("{")[0]
    else:
        print(f"Failed to create release: {response.status_code}")
        print(f"Response: {response.text}")
        return None, None

# 3. Upload APK
def upload_apk_to_github(release_id, upload_url, apk_path):
    print(f"Uploading APK: {apk_path}")
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/vnd.android.package-archive",
        "Accept": "application/vnd.github.v3+json"
    }
    
    file_name = os.path.basename(apk_path)
    
    # 既存のアセットをチェック
    assets_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/{release_id}/assets"
    response = requests.get(assets_url, headers=headers)
    
    if response.status_code == 200:
        assets = response.json()
        for asset in assets:
            if asset["name"] == file_name:
                print(f"Asset {file_name} already exists. Deleting...")
                delete_response = requests.delete(asset["url"], headers=headers)
                if delete_response.status_code == 204:
                    print(f"Deleted existing asset: {file_name}")
    
    # 新しいAPKをアップロード
    with open(apk_path, "rb") as apk_file:
        response = requests.post(f"{upload_url}?name={file_name}", headers=headers, data=apk_file)
    
    if response.status_code == 201:
        print(f"Successfully uploaded {file_name}")
        return True
    else:
        print(f"Failed to upload {file_name}: {response.status_code}")
        print(f"Response: {response.text}")
        return False

# 4. Execution of all processes
def release_apks():
    print("Starting APK release process...")
    
    # バージョン情報を抽出
    version, release_id = extract_version_and_release_id()
    if not version or not release_id:
        print("Could not extract version information.")
        return
    
    print(f"Using version: {version}, release_id: {release_id}")
    
    # GitHubリリースを作成
    github_release_id, upload_url = create_github_release(version, release_id)
    if not github_release_id:
        print("Failed to create GitHub release.")
        return
    
    # patched_apksディレクトリが存在するか確認
    if not os.path.exists(APK_DIR):
        print(f"Directory {APK_DIR} does not exist. Checking for any APK files...")
        
        # ダウンロードディレクトリから直接アップロードを試みる
        if os.path.exists(DOWNLOAD_DIR):
            for apk_name in os.listdir(DOWNLOAD_DIR):
                if apk_name.endswith(".apk"):
                    apk_path = os.path.join(DOWNLOAD_DIR, apk_name)
                    print(f"Uploading downloaded APK: {apk_path}")
                    upload_apk_to_github(github_release_id, upload_url, apk_path)
        return
    
    # patched_apksディレクトリからAPKをアップロード
    print(f"Looking for APK files in {APK_DIR}...")
    apk_files = [f for f in os.listdir(APK_DIR) if f.endswith(".apk")]
    
    if not apk_files:
        print(f"No APK files found in {APK_DIR}")
        return
    
    for apk_file in apk_files:
        apk_path = os.path.join(APK_DIR, apk_file)
        print(f"Processing APK: {apk_path}")
        upload_apk_to_github(github_release_id, upload_url, apk_path)
    
    print("APK release process completed.")

if __name__ == "__main__":
    release_apks()
