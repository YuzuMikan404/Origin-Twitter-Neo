#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Origin Twitter Neo: Piko パッチ済み Twitter APK から、テーマカラー別 APK を作る。

設計方針:
  * 1 色でも失敗したら終了コード 1 で終わる（部分的なリリースを作らない）
  * 署名情報は環境変数のみ（デフォルトのパスワードは持たない）
  * apktool.yml / AndroidManifest.xml はテキスト編集（再シリアライズによる破損を避ける）
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

KEYSTORE_PATH = os.environ.get("KEYSTORE_PATH", "./origin-twitter.keystore")
DOWNLOADS_DIR = Path("downloads")
OUTPUT_DIR = Path("patched_apks")
BUILD_MANIFEST = OUTPUT_DIR / "build-manifest.json"
TOOL_TIMEOUT = int(os.environ.get("APKTOOL_TIMEOUT", "1800"))  # 秒

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
    "ffadc0": "MateChan",
}

ANDROID_NS = "http://schemas.android.com/apk/res/android"


# --------------------------------------------------------------------------
# ツール検出・実行
# --------------------------------------------------------------------------
def find_apktool() -> list[str]:
    """動作する apktool コマンドを返す。見つからなければ SystemExit。"""
    candidates: list[list[str]] = []
    jar = os.environ.get("APKTOOL_JAR")
    if jar:
        candidates.append(["java", "-jar", jar])
    exe = shutil.which("apktool")
    if exe:
        candidates.append([exe])

    for cmd in candidates:
        try:
            result = subprocess.run(
                cmd + ["--version"], capture_output=True, text=True, timeout=60, check=False
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"Warning: {' '.join(cmd)} raised {exc!r}")
            continue
        if result.returncode == 0:
            print(f"✅ apktool: {' '.join(cmd)} (version {result.stdout.strip()})")
            return cmd

    sys.exit("❌ FATAL: no working apktool found (install it or set APKTOOL_JAR).")


def _version_key(name: str) -> tuple[int, ...]:
    return tuple(int(p) for p in name.split("."))


def find_android_tool(tool: str) -> str:
    """最新の build-tools から zipalign / apksigner を探す。"""
    for env_name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        root = os.environ.get(env_name)
        if not root:
            continue
        build_tools = Path(root) / "build-tools"
        if not build_tools.is_dir():
            continue
        versions = sorted(
            (p for p in build_tools.iterdir() if re.fullmatch(r"\d+(\.\d+)*", p.name)),
            key=lambda p: _version_key(p.name),
            reverse=True,
        )
        for version_dir in versions:
            candidate = version_dir / tool
            if candidate.is_file():
                return str(candidate)

    found = shutil.which(tool)
    if found:
        return found
    sys.exit(f"❌ FATAL: Android build-tool '{tool}' not found (set ANDROID_HOME).")


def run_checked(cmd: list[str], what: str) -> subprocess.CompletedProcess:
    """コマンドを実行し、失敗時は出力を表示して CalledProcessError を送出。"""
    env = os.environ.copy()
    env.setdefault("JAVA_OPTS", "-Xmx6g")  # OOM 対策
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=env, timeout=TOOL_TIMEOUT, check=False
    )
    if result.returncode != 0:
        print(f"{what} failed (exit {result.returncode}):")
        print("stderr:\n" + (result.stderr.strip() or "(empty)"))
        print("stdout:\n" + (result.stdout.strip() or "(empty)"))
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


# --------------------------------------------------------------------------
# apktool d / b
# --------------------------------------------------------------------------
def decompile_apk(apktool: list[str], apk_path: Path, output_dir: Path) -> None:
    print(f"Decompiling to: {output_dir}")
    shutil.rmtree(output_dir, ignore_errors=True)
    run_checked(apktool + ["d", "-f", str(apk_path), "-o", str(output_dir)], "Decompile")
    print("✅ Decompilation completed")


def recompile_apk(apktool: list[str], decompiled_dir: Path, output_apk: Path) -> None:
    print(f"Recompiling to: {output_apk}")
    run_checked(apktool + ["b", str(decompiled_dir), "-o", str(output_apk)], "Recompile")
    if not output_apk.is_file() or output_apk.stat().st_size == 0:
        raise RuntimeError(f"apktool reported success but {output_apk} is missing/empty")
    print("✅ Recompilation succeeded")


# --------------------------------------------------------------------------
# パッチ処理
# --------------------------------------------------------------------------
def fix_webview_xml(decompiled_dir: Path) -> None:
    """layout XML の '+@id/' を '@+id/' に置換する（webview.xml エラー対策）。"""
    layout_dir = decompiled_dir / "res" / "layout"
    if not layout_dir.is_dir():
        print(f"  No layout directory found in {decompiled_dir}")
        return

    fixed = 0
    for xml_path in layout_dir.glob("*.xml"):
        content = xml_path.read_text(encoding="utf-8")
        new_content = re.sub(r"\+@id/([A-Za-z0-9_]+)", r"@+id/\1", content)
        if new_content != content:
            xml_path.write_text(new_content, encoding="utf-8")
            fixed += 1
            print(f"  Fixed ID reference in: {xml_path.name}")

    print(f"  ✓ Fixed {fixed} layout XML file(s)" if fixed else "  No +@id/ references needed fixing")


def update_apktool_yml(decompiled_dir: Path) -> None:
    """doNotCompress に '.so' を追加する（テキスト編集。YAML の再出力はしない）。"""
    yml_path = decompiled_dir / "apktool.yml"
    if not yml_path.is_file():
        return

    lines = yml_path.read_text(encoding="utf-8").splitlines()
    key_idx = next((i for i, ln in enumerate(lines) if ln.startswith("doNotCompress:")), None)

    if key_idx is None:
        lines += ["doNotCompress:", "- .so"]
    else:
        inline = lines[key_idx].split(":", 1)[1].strip()
        if inline == "[]":
            lines[key_idx : key_idx + 1] = ["doNotCompress:", "- .so"]
        else:
            end = key_idx + 1
            while end < len(lines) and re.match(r"^\s*-\s", lines[end]):
                end += 1
            items = {ln.strip()[1:].strip().strip("'\"") for ln in lines[key_idx + 1 : end]}
            if ".so" not in items:
                indent = re.match(r"^(\s*)-", lines[end - 1])
                prefix = indent.group(1) if indent and end - 1 > key_idx else ""
                lines.insert(end, f"{prefix}- .so")

    yml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def modify_manifest(decompiled_dir: Path) -> None:
    """<application> に android:extractNativeLibs="true" を設定する（テキスト編集）。"""
    manifest = decompiled_dir / "AndroidManifest.xml"
    if not manifest.is_file():
        return

    text = manifest.read_text(encoding="utf-8")
    match = re.search(r"<application\b[^>]*>", text, flags=re.S)
    if not match:
        print("  Warning: <application> not found in AndroidManifest.xml")
        return

    tag = match.group(0)
    attr = 'android:extractNativeLibs="true"'
    if "android:extractNativeLibs" in tag:
        new_tag = re.sub(r'android:extractNativeLibs="[^"]*"', attr, tag)
    else:
        new_tag = tag.replace("<application", f"<application {attr}", 1)

    if new_tag != tag:
        manifest.write_text(text[: match.start()] + new_tag + text[match.end() :], encoding="utf-8")


def modify_xml(decompiled_dir: Path) -> None:
    for rel in ("res/layout/ocf_twitter_logo.xml", "res/layout/login_toolbar_seamful_custom_view.xml"):
        path = decompiled_dir / rel
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        content = content.replace("?dynamicColorGray1100", "@color/twitter_blue")
        content = content.replace("@color/gray_1100", "@color/twitter_blue")
        content = re.sub(r"#ff1d9bf0|#ff1da1f2", "@color/twitter_blue", content, flags=re.IGNORECASE)
        path.write_text(content, encoding="utf-8")


def modify_styles(decompiled_dir: Path) -> None:
    styles_path = decompiled_dir / "res/values/styles.xml"
    if not styles_path.is_file():
        return
    tree = ET.parse(styles_path)
    for style in tree.getroot().findall("style"):
        name = style.get("name", "")
        if name in ("TwitterBase.Dim", "TwitterBase.LightsOut", "TwitterBase.Standard"):
            for item in style.findall("item"):
                if item.get("name") == "coreColorBadgeVerified":
                    item.text = "@color/blue_500"
        elif name in ("PaletteDim", "PaletteLightsOut", "PaletteStandard"):
            for item in style.findall("item"):
                if item.get("name") == "abstractColorUnread":
                    item.text = "@color/twitter_blue_opacity_50"
                elif item.get("name") == "abstractColorLink" and name == "PaletteStandard":
                    item.text = "@color/twitter_blue"
        elif name == "Theme.LaunchScreen":
            for item in style.findall("item"):
                if item.get("name") == "windowSplashScreenBackground":
                    item.text = "@color/twitter_blue"
    tree.write(styles_path, encoding="utf-8", xml_declaration=True)


def modify_colors(decompiled_dir: Path, color_hex: str) -> None:
    colors_path = decompiled_dir / "res/values/colors.xml"
    if not colors_path.is_file():
        return
    tree = ET.parse(colors_path)
    overrides = {
        "twitter_blue": f"#ff{color_hex}",
        "deep_transparent_twitter_blue": f"#cc{color_hex}",
        "twitter_blue_opacity_30": f"#4d{color_hex}",
        "twitter_blue_opacity_50": f"#80{color_hex}",
        "twitter_blue_opacity_58": f"#95{color_hex}",
    }
    for tag in tree.getroot().findall("color"):
        name = tag.get("name", "")
        if name in overrides:
            tag.text = overrides[name]
    tree.write(colors_path, encoding="utf-8", xml_declaration=True)


def hex_to_smali(hex_color: str) -> str:
    int_color = int(hex_color, 16)
    smali_int = (int_color ^ 0xFFFFFF) + 1
    return f"-0x{smali_int:06x}".lower()


def modify_smali(decompiled_dir: Path, color_hex: str) -> None:
    smali_color = hex_to_smali(color_hex) + "00000000L"
    patterns = {
        re.compile(r"-0xe2641000000000L", re.IGNORECASE): smali_color,
        re.compile(r"0xff1d9bf0L", re.IGNORECASE): f"0xff{color_hex}L",
    }
    changed = 0
    for smali_path in decompiled_dir.rglob("*.smali"):
        try:
            content = smali_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new_content = content
        for pattern, replacement in patterns.items():
            new_content = pattern.sub(replacement, new_content)
        if new_content != content:
            smali_path.write_text(new_content, encoding="utf-8")
            changed += 1

    print(f"  smali: patched {changed} file(s)")
    if changed == 0:
        print("  ⚠️ Warning: no smali color constants matched; the app may have changed upstream.")


# --------------------------------------------------------------------------
# 署名
# --------------------------------------------------------------------------
def require_signing_env() -> None:
    missing = [n for n in ("STOREPASS", "KEYPASS", "ALIAS") if not os.environ.get(n)]
    if missing:
        sys.exit(f"❌ Missing required environment variable(s): {', '.join(missing)}")
    if not Path(KEYSTORE_PATH).is_file():
        sys.exit(f"❌ Keystore not found: {KEYSTORE_PATH}")


def sign_apk(unsigned_apk: Path, signed_apk: Path) -> None:
    print(f"Signing: {unsigned_apk.name}")
    aligned = unsigned_apk.with_suffix(".aligned.apk")
    try:
        # zipalign の失敗は致命的（不整合な APK を黙って署名しない）
        run_checked([find_android_tool("zipalign"), "-f", "4", str(unsigned_apk), str(aligned)], "zipalign")

        apksigner = find_android_tool("apksigner")
        # パスワードはコマンドラインに出さず、環境変数経由で渡す
        run_checked(
            [
                apksigner, "sign",
                "--ks", KEYSTORE_PATH,
                "--ks-pass", "env:STOREPASS",
                "--ks-key-alias", os.environ["ALIAS"],
                "--key-pass", "env:KEYPASS",
                "--out", str(signed_apk),
                str(aligned),
            ],
            "apksigner sign",
        )
        run_checked([apksigner, "verify", str(signed_apk)], "apksigner verify")
    finally:
        aligned.unlink(missing_ok=True)
        Path(str(signed_apk) + ".idsig").unlink(missing_ok=True)
    print(f"✅ Signed & verified: {signed_apk.name}")


# --------------------------------------------------------------------------
# メイン
# --------------------------------------------------------------------------
def parse_version(apk_version: str) -> tuple[str, str]:
    match = re.search(r"(\d+\.\d+\.\d+)-release\.(\d+)", apk_version)
    if match:
        return match.group(1), match.group(2)
    return apk_version.split("-release")[0].split("-")[0], "0"


def main() -> None:
    apk_version = os.environ.get("APK_VERSION") or os.environ.get("monsivamon_TAG")
    if not apk_version or apk_version.lower() in ("null", "none"):
        sys.exit("Error: APK_VERSION is not set or invalid.")
    print(f"APK version: {apk_version}")

    apks = sorted(DOWNLOADS_DIR.glob("*.apk")) if DOWNLOADS_DIR.is_dir() else []
    if not apks:
        sys.exit(f"Error: No APK file found in {DOWNLOADS_DIR}/")
    apk_path = apks[0]
    print(f"Found APK: {apk_path}")

    require_signing_env()
    apktool = find_apktool()
    find_android_tool("zipalign")  # 早期チェック
    find_android_tool("apksigner")

    clean_version, release_id = parse_version(apk_version)
    print(f"Clean version: {clean_version}, Release ID: {release_id}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    built: list[str] = []
    failed: list[str] = []

    for color_hex, color_name in THEME_COLORS.items():
        print("\n" + "=" * 70)
        print(f"Processing {color_name} theme (color: #{color_hex})")
        print("=" * 70)

        work_dir = Path(f"decompiled-twitter-{clean_version}-{color_name}")
        unsigned = OUTPUT_DIR / f"unsigned-{color_name}.apk"
        final_name = f"Origin-Twitter-Neo.{color_name}.v{clean_version}-release.{release_id}.apk"
        final_path = OUTPUT_DIR / final_name

        try:
            decompile_apk(apktool, apk_path, work_dir)
            fix_webview_xml(work_dir)
            update_apktool_yml(work_dir)
            modify_manifest(work_dir)
            modify_xml(work_dir)
            modify_styles(work_dir)
            modify_colors(work_dir, color_hex)
            modify_smali(work_dir, color_hex)
            recompile_apk(apktool, work_dir, unsigned)
            sign_apk(unsigned, final_path)
            built.append(final_name)
            print(f"✅ Successfully created: {final_name}")
        except Exception as exc:  # noqa: BLE001 - 1 色の失敗で他の色のログ取得を止めない
            failed.append(color_name)
            print(f"❌ Error processing {color_name}: {exc!r}")
            if not isinstance(exc, subprocess.CalledProcessError):
                traceback.print_exc()
            final_path.unlink(missing_ok=True)
        finally:
            unsigned.unlink(missing_ok=True)
            shutil.rmtree(work_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print(f"Built {len(built)}/{len(THEME_COLORS)} variant(s)")

    if failed:
        # 部分的な成果物をリリースさせないため、manifest は書かずに異常終了する
        BUILD_MANIFEST.unlink(missing_ok=True)
        sys.exit(f"❌ Failed variants: {', '.join(failed)}")

    BUILD_MANIFEST.write_text(
        json.dumps({"apk_version": apk_version, "files": built}, indent=2), encoding="utf-8"
    )
    print("All color variants processed!")


if __name__ == "__main__":
    main()
