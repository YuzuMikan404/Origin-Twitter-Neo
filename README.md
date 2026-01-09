# Origin Twitter Neo

![GitHub Downloads](https://img.shields.io/github/downloads/YuzuMikan404/Origin-Twitter-Neo/total?color=green&style=for-the-badge&logo=github)
![GitHub Issues](https://img.shields.io/github/stars/YuzuMikan404/Origin-Twitter-Neo?style=for-the-badge&logo=github)

## 概要
**Origin Twitter Neo**は、[monefiera](https://github.com/monefiera)さんの[Origin-Twitter](https://github.com/monefiera/Origin-Twitter)をベースに、参照元を更新して自動ビルドするようにした自分用ビルドリポジトリです。
参照元であったcrimeraさんのAPK更新が停止していたため、独自に参照元を[crimera/twitter-apk](https://github.com/crimera/twitter-apk/releases)から[lluni/twitter-apk](https://github.com/lluni/twitter-apk)にに変更してビルドしています。
**自己責任**にてご使用ください。

## 📢 アナウンス
- **参照元リポジトリ変更のお知らせ（2026/01/10更新）**
  参照元リポジトリを[monsivamon/twitter-apk](https://github.com/monsivamon/twitter-apk/releases) にしていましたが、[v11.53.0-release.0](https://github.com/YuzuMikan404/Origin-Twitter-Neo/releases/tag/11.53.0-release.0)にて参照元リポジトリの不具合なのかクラッシュするAPKを参照してしまいましたので、[lluni/twitter-apk](https://github.com/lluni/twitter-apk)にに変更してビルドしています。
- **ログイン不具合の解決策 (2026/01/05更新)**
  元パッチの影響でログインできない不具合がありましたが、応急的な解決策が判明しました。[こちらの手順](https://github.com/crimera/piko/issues/714#issuecomment-3706542446)を実施することでログインができるようになるかもしれません。私の環境ではこの方法でログインできました。<br>
  また、ADBにてGoogle Playからインストールしたと見せかけることにより、ログインができるという情報もあります。Obtainiumの設定からも偽装することができます。
- **署名の変更について (2025/12/27更新)**
  署名がされていない不具合を修正しました。これに伴い署名キーが変更されたため、以前のバージョンからは上書きアップデートができない場合があります。その際は一度アンインストールしてから再インストールしてください。それに伴い、これ以前のリリースは削除しています。これ以降、署名は変更しません。
- **Blueskyでのご紹介について**
  monefieraさんがご自身のBlueskyでこのリポジトリを紹介してくださっていました。勝手にフォークして作成したにも関わらず、ありがとうございます！🙇🏻
  [該当ポストはこちら](https://bsky.app/profile/forsaken-love02.bsky.social/post/3m7nixn7t4k2a)

## 📥 ダウンロード
[Obtainium](https://github.com/ImranR98/Obtainium)を使用して、更新を自動で追跡・インストールすることをお勧めします。

[<img src="badge_obtainium.png" alt="Get it on Obtainium" height="45">](https://apps.obtainium.imranr.dev/redirect?r=obtainium://app/%7B%22id%22%3A%22com.twitter.android%22%2C%22url%22%3A%22https%3A%2F%2Fgithub.com%2FYuzuMikan404%2FOrigin-Twitter-Neo%22%2C%22author%22%3A%22YuzuMikan404%22%2C%22name%22%3A%22Twitter%22%2C%22preferredApkIndex%22%3A9%2C%22additionalSettings%22%3A%22%7B%5C%22includePrereleases%5C%22%3Afalse%2C%5C%22fallbackToOlderReleases%5C%22%3Atrue%2C%5C%22filterReleaseTitlesByRegEx%5C%22%3A%5C%22%5C%22%2C%5C%22filterReleaseNotesByRegEx%5C%22%3A%5C%22%5C%22%2C%5C%22verifyLatestTag%5C%22%3Afalse%2C%5C%22sortMethodChoice%5C%22%3A%5C%22date%5C%22%2C%5C%22useLatestAssetDateAsReleaseDate%5C%22%3Afalse%2C%5C%22releaseTitleAsVersion%5C%22%3Afalse%2C%5C%22trackOnly%5C%22%3Afalse%2C%5C%22versionExtractionRegEx%5C%22%3A%5C%22%5C%22%2C%5C%22matchGroupToUse%5C%22%3A%5C%22%5C%22%2C%5C%22versionDetection%5C%22%3Afalse%2C%5C%22releaseDateAsVersion%5C%22%3Afalse%2C%5C%22useVersionCodeAsOSVersion%5C%22%3Afalse%2C%5C%22apkFilterRegEx%5C%22%3A%5C%22%5C%22%2C%5C%22invertAPKFilter%5C%22%3Afalse%2C%5C%22autoApkFilterByArch%5C%22%3Atrue%2C%5C%22appName%5C%22%3A%5C%22%5C%22%2C%5C%22appAuthor%5C%22%3A%5C%22%5C%22%2C%5C%22shizukuPretendToBeGooglePlay%5C%22%3Afalse%2C%5C%22allowInsecure%5C%22%3Afalse%2C%5C%22exemptFromBackgroundUpdates%5C%22%3Afalse%2C%5C%22skipUpdateNotifications%5C%22%3Afalse%2C%5C%22about%5C%22%3A%5C%22%5C%22%2C%5C%22refreshBeforeDownload%5C%22%3Afalse%2C%5C%22includeZips%5C%22%3Afalse%2C%5C%22zippedApkFilterRegEx%5C%22%3A%5C%22%5C%22%7D%22%2C%22overrideSource%22%3Anull%7D)

または [リリース](https://github.com/YuzuMikan404/Origin-Twitter-Neo/releases) ページから直接APKをダウンロードしてください。

## 🎨 カラーバリエーション
お好みに合わせて、以下の10色から選べます。
※すべての署名は共通化されているため、アプリを再インストールすることで色のみを変更可能です。

### ① Twitter Web準拠カラー
| 色名 | カラーコード | 備考 |
| :--- | :--- | :--- |
| 💧 **Origin Blue** | `#1d9bf0` | |
| ⭐ **Star Gold** | `#fed400` | |
| 🌸 **Sakura Red** | `#f91880` | |
| 🐙 **Octopus Purple** | `#7856ff` | |
| 🔥 **Flare Orange** | `#ff7a00` | |
| 🥑 **Avocado Green** | `#31c88e` | |

### ② FIERA's オリジナルカラー
| 色名 | カラーコード | 備考 |
| :--- | :--- | :--- |
| 🌹 **Crimsonate** | `#c20024` | 深紅のテーマ |
| 💎 **Izumo Lazurite** | `#1e50a2` | 落ち着いた瑠璃色 |
| ☁ **Monotone** | `#808080` | グレー基調 |
| 🩷 **MateChan Pink** | `#ffadc0` | 淡いピンク |

## 💐 クレジット
- **[crimera](https://github.com/crimera)**: Base Patches (Piko) Developer
- **[monefiera](https://github.com/monefiera)**: Original "Origin Twitter" Developer
- **[Twitter, Inc.](https://twitter.com)**: Original App Developer
Based on [Piko Patches](https://github.com/crimera/piko)

### 法的免責事項および著作権に関する表記

本ソフトウェア（以下「本プロジェクト」）は、技術的な研究および教育を目的として作成された非公式の成果物です。本プロジェクトの開発者は、X Corp.（旧Twitter, Inc.）およびその関連企業といかなる提携関係にもなく、また公式に認可されたものではありません。

本プロジェクトにおいて参照、利用、または表示される「Twitter」、「X」、および関連するロゴ、名称、商標、サービスマーク等の知的財産権は、すべてX Corp.またはそれぞれの権利所有者に帰属します。

本プロジェクトは、著作権法および関連法規の侵害を意図したものではありません。本プロジェクトの機能およびコードは、公正な慣行（Fair Use）の範囲内での利用を想定しており、オリジナルサービスの市場価値を毀損すること、または権利者の利益を不当に害することを目的としていません。

権利所有者からの要請があった場合、または本プロジェクトが規約違反であると判断された場合、開発者は速やかに該当するコンテンツの削除、またはプロジェクトの公開停止措置を講じます。

本プロジェクトの使用によって生じたいかなる損害（アカウントの凍結、データ損失、法的措置等を含むがこれらに限定されない）について、開発者は一切の責任を負いません。利用者は自身の責任において本プロジェクトを使用するものとします。

### Legal Disclaimer and Copyright Notice

This software (hereinafter referred to as "this Project") is an unofficial derivative work developed strictly for educational and technical research purposes. The developer of this Project is not affiliated with, endorsed by, or associated with X Corp. (formerly Twitter, Inc.) or any of its subsidiaries.

All trademarks, logos, service marks, and trade names of "Twitter," "X," and related intellectual property referenced, used, or displayed in this Project remain the sole property of X Corp. or their respective owners.

This Project is NOT intended to infringe upon any copyright laws or related regulations. The code and functionality provided herein are intended for use within the bounds of fair use and do not aim to diminish the market value of the original service or unfairly prejudice the interests of the rights holders.

In the event of a request from the rights holder, or if this Project is deemed to violate any terms of service, the developer agrees to promptly remove the offending content or cease publication of the Project.

The developer assumes no liability for any damages (including, but not limited to, account suspension, data loss, or legal action) arising from the use of this Project. Users agree to use this Project at their own risk.
