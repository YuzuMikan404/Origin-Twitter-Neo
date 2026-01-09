#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import sys
import glob

GITHUB_REPO = "YuzuMikan404/Origin-Twitter-Neo"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN environment variable is not set.")
    sys.exit(1)

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
APK_DIR = "patched_apks"

def get_tag():
    tag = os.getenv("monsivamon_TAG")
    if not tag:
        print("❌ Error: monsivamon_TAG is not set.")
        sys.exit(1)
    print(f"Using tag: {tag}")
    return tag

def create_github_release(tag):
    print(f"Creating GitHub release with tag: {tag}")

    is_prerelease = "beta" in tag.lower()
    if is_prerelease:
        print("⚠️ This will be created as a PRE-RELEASE")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 既存リリース確認
    response = requests.get(GITHUB_API, headers=headers)
    if response.status_code == 200:
        for release in response.json():
            if release.get("tag_name") == tag:
                print(f"✅ Release {tag} already exists.")
                return release["id"], release["upload_url"].split("{")[0]

    body = f"Auto Release: Origin Twitter Neo {tag}"

    data = {
        "tag_name": tag,
        "name": f"Origin Twitter Neo {tag}",
        "body": body,
        "draft": False,
        "prerelease": is_prerelease
    }

    response = requests.post(GITHUB_API, json=data, headers=headers)
    print(f"Create release response status: {response.status_code}")

    if response.status_code == 201:
        info = response.json()
        print(f"✅ GitHub Release created: {info['html_url']}")
        return info["id"], info["upload_url"].split("{")[0]
    else:
        print(f"❌ Failed to create release: {response.status_code}")
        print(response.text)
        sys.exit(1)

def upload_apk_to_github(release_id, upload_url, apk_path):
    print(f"Uploading {os.path.basename(apk_path)}")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/vnd.android.package-archive",
        "Accept": "application/vnd.github.v3+json"
    }

    file_name = os.path.basename(apk_path)

    with open(apk_path, "rb") as f:
        r = requests.post(f"{upload_url}?name={file_name}", headers=headers, data=f)

    if r.status_code == 201:
        print(f"✅ Uploaded {file_name}")
        return True
    else:
        print(f"❌ Upload failed {file_name}: {r.status_code}")
        print(r.text)
        return False

def release_apks():
    print("Starting APK release process...")

    tag = get_tag()

    release_id, upload_url = create_github_release(tag)

    apk_files = sorted(glob.glob(os.path.join(APK_DIR, "*.apk")))
    if not apk_files:
        print("❌ No APK files found.")
        sys.exit(1)

    print(f"Found {len(apk_files)} APK(s)")

    ok = 0
    for apk in apk_files:
        if upload_apk_to_github(release_id, upload_url, apk):
            ok += 1

    print(f"✅ Done: {ok}/{len(apk_files)} uploaded")

if __name__ == "__main__":
    release_apks()
