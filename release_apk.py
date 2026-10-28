#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patched_apks/ の APK を GitHub Release にアップロードする。

設計方針:
  * まず draft で作成 → 全 APK のアップロード完了を確認 → 最後に公開
    （途中で失敗しても公開済みの不完全リリースが残らず、次回実行で再試行される）
  * 再実行しても安全（同名・同サイズのアセットはスキップ、違えば置換）
  * ネットワークエラー・レート制限にはリトライ
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
REPO = os.environ.get("GITHUB_REPOSITORY", "YuzuMikan404/Origin-Twitter-Neo")
UPSTREAM_REPO = "monsivamon/twitter-apk"
APK_DIR = Path("patched_apks")
BUILD_MANIFEST = APK_DIR / "build-manifest.json"
UPLOAD_ATTEMPTS = 3
PRERELEASE_MARKERS = ("-dev.", "-dev-", "-beta", "-rc.", "-rc-", "-alpha")


def make_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "PATCH", "DELETE"}),  # POST は自前で冪等に再試行
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def get_release_tag() -> str:
    tag = os.getenv("RELEASE_TAG")
    if not tag:
        apk_version = os.getenv("APK_VERSION", "")
        piko_patch = os.getenv("PIKO_RELEASE_TAG", "").removeprefix("piko-v")
        if apk_version and piko_patch:
            tag = f"{apk_version}_{piko_patch}"
    if not tag:
        sys.exit("❌ Error: RELEASE_TAG is not set.")
    print(f"Using release tag: {tag}")
    return tag


def is_prerelease(tag: str) -> bool:
    value = os.getenv("PIKO_PRERELEASE", "").strip().lower()
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False
    combined = f"{tag} {os.getenv('PIKO_RELEASE_TAG', '')}".lower()
    return any(marker in combined for marker in PRERELEASE_MARKERS)


def load_expected_files() -> list[Path]:
    """今回のビルドで作られたはずの APK の一覧を返し、欠けていれば異常終了する。"""
    if BUILD_MANIFEST.is_file():
        names = json.loads(BUILD_MANIFEST.read_text(encoding="utf-8")).get("files", [])
        files = [APK_DIR / n for n in names]
    else:
        print("⚠️ build-manifest.json not found; falling back to *.apk glob")
        files = sorted(APK_DIR.glob("*.apk"))

    if not files:
        sys.exit("❌ No APK files to release.")
    bad = [f.name for f in files if not f.is_file() or f.stat().st_size == 0]
    if bad:
        sys.exit(f"❌ Missing or empty APK file(s): {', '.join(bad)}")
    return files


def find_release(session: requests.Session, tag: str) -> dict | None:
    """draft を含めてタグ名でリリースを探す。"""
    for page in range(1, 11):
        resp = session.get(f"{API}/repos/{REPO}/releases", params={"per_page": 100, "page": page}, timeout=30)
        resp.raise_for_status()
        releases = resp.json()
        for release in releases:
            if release.get("tag_name") == tag:
                return release
        if len(releases) < 100:
            break
    return None


def build_body(tag: str, prerelease: bool) -> str:
    piko_tag = os.getenv("PIKO_RELEASE_TAG", "")
    apk_version = os.getenv("APK_VERSION", "")
    body = f"Auto Release: Origin Twitter Neo {tag}<br>"
    body += f"Build from: [{piko_tag}](https://github.com/{UPSTREAM_REPO}/releases/tag/{piko_tag})"
    if apk_version:
        body += f"<br>Twitter APK: v{apk_version}"
    if piko_tag:
        body += f"<br>Piko patch: v{piko_tag.removeprefix('piko-v')}"
    if prerelease:
        body += "<br><br>⚠️ This is a pre-release build based on an upstream pre-release."
    return body


def get_or_create_release(session: requests.Session, tag: str, prerelease: bool) -> dict:
    release = find_release(session, tag)
    if release:
        state = "draft" if release.get("draft") else "published"
        print(f"✅ Release {tag} already exists ({state}); reusing it.")
        return release

    print(f"Creating draft release: {tag}")
    payload = {
        "tag_name": tag,
        "name": f"Origin Twitter Neo {tag}",
        "body": build_body(tag, prerelease),
        "draft": True,
        "prerelease": prerelease,
    }
    last_error = ""
    for attempt in range(1, 4):
        try:
            resp = session.post(f"{API}/repos/{REPO}/releases", json=payload, timeout=30)
            if resp.status_code == 201:
                return resp.json()
            last_error = f"{resp.status_code}: {resp.text}"
        except requests.RequestException as exc:
            last_error = repr(exc)
        # 通信エラー等で実は作成済みだった場合に重複させない
        existing = find_release(session, tag)
        if existing:
            return existing
        print(f"⚠️ Create release failed (attempt {attempt}/3): {last_error}")
        time.sleep(5 * attempt)
    sys.exit(f"❌ Failed to create release: {last_error}")


def upload_asset(session: requests.Session, release_id: int, upload_url: str, apk: Path) -> bool:
    size = apk.stat().st_size
    print(f"Uploading {apk.name} ({size / 1_048_576:.1f} MiB)")

    for attempt in range(1, UPLOAD_ATTEMPTS + 1):
        try:
            resp = session.get(f"{API}/repos/{REPO}/releases/{release_id}", timeout=30)
            resp.raise_for_status()
            existing = {a["name"]: a for a in resp.json().get("assets", [])}

            asset = existing.get(apk.name)
            if asset:
                if asset.get("state") == "uploaded" and asset.get("size") == size:
                    print(f"  ↪ already uploaded, skipping: {apk.name}")
                    return True
                session.delete(f"{API}/repos/{REPO}/releases/assets/{asset['id']}", timeout=30)

            with apk.open("rb") as fh:
                up = session.post(
                    upload_url,
                    params={"name": apk.name},
                    headers={"Content-Type": "application/vnd.android.package-archive"},
                    data=fh,
                    timeout=(30, 900),
                )
            if up.status_code == 201:
                print(f"✅ Uploaded {apk.name}")
                return True
            print(f"⚠️ Upload failed (attempt {attempt}/{UPLOAD_ATTEMPTS}): {up.status_code} {up.text[:300]}")
        except requests.RequestException as exc:
            print(f"⚠️ Upload error (attempt {attempt}/{UPLOAD_ATTEMPTS}): {exc!r}")
        time.sleep(5 * attempt)
    return False


def publish_release(session: requests.Session, release_id: int, prerelease: bool) -> None:
    resp = session.patch(
        f"{API}/repos/{REPO}/releases/{release_id}",
        json={"draft": False, "prerelease": prerelease},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"❌ Failed to publish release: {resp.status_code} {resp.text}")
    print(f"✅ Published: {resp.json().get('html_url')}")


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Error: GITHUB_TOKEN environment variable is not set.")

    tag = get_release_tag()
    prerelease = is_prerelease(tag)
    print("⚠️ Upstream is pre-release" if prerelease else "ℹ️ Upstream is stable release")

    files = load_expected_files()
    print(f"Found {len(files)} APK(s) to release")

    session = make_session(token)
    release = get_or_create_release(session, tag, prerelease)
    upload_url = release["upload_url"].split("{")[0]

    failed = [f.name for f in files if not upload_asset(session, release["id"], upload_url, f)]
    if failed:
        sys.exit(
            f"❌ Upload failed for: {', '.join(failed)}\n"
            "   The release was left as a draft and will be retried on the next run."
        )

    # 公開前に、期待する全アセットが揃っていることを最終確認
    resp = session.get(f"{API}/repos/{REPO}/releases/{release['id']}", timeout=30)
    resp.raise_for_status()
    uploaded = {a["name"] for a in resp.json().get("assets", []) if a.get("state") == "uploaded"}
    missing = [f.name for f in files if f.name not in uploaded]
    if missing:
        sys.exit(f"❌ Assets missing after upload: {', '.join(missing)}")

    if release.get("draft") or release.get("prerelease") != prerelease:
        publish_release(session, release["id"], prerelease)
    print(f"✅ Done: {len(files)}/{len(files)} uploaded")


if __name__ == "__main__":
    main()
