name: Auto Patch & Release APK

on:
  workflow_dispatch:

jobs:
  patch_and_release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: "3.9"

      - name: Get latest release info from GitHub
        id: get_release_piko_and_origin
        run: |
          monsivamon_TAG=$(curl -s https://api.github.com/repos/monsivamon/twitter-apk/releases/latest | jq -r .tag_name)
          echo "monsivamon_TAG=${monsivamon_TAG}" >> $GITHUB_ENV
          YuzuMikan404_TAG=$(curl -s https://api.github.com/repos/YuzuMikan404/Origin-Twitter/releases/latest | jq -r .tag_name)
          echo "YuzuMikan404_TAG=${YuzuMikan404_TAG}" >> $GITHUB_ENV

      - name: Check if releases match
        id: check_releases
        run: |
          if [ "${{ env.monsivamon_TAG }}" == "${{ env.YuzuMikan404_TAG }}" ]; then
            echo "Releases match. Skipping download and processing."
            echo "SKIP=true" >> $GITHUB_ENV
          else
            echo "Releases differ. Proceeding with download and processing."
            echo "SKIP=false" >> $GITHUB_ENV
          fi

      - name: Install requests and PyYAML
        if: ${{ env.SKIP == 'false' }}
        run: pip install requests PyYAML

      - name: Install dependencies
        if: ${{ env.SKIP == 'false' }}
        run: |
          sudo apt-get update && sudo apt-get install -y curl wget jq unzip openjdk-17-jdk

      - name: Install Android SDK & Build Tools
        if: ${{ env.SKIP == 'false' }}
        run: |
          wget https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O sdk-tools.zip
          unzip sdk-tools.zip
          mkdir -p $HOME/android-sdk/cmdline-tools
          mv cmdline-tools $HOME/android-sdk/cmdline-tools/latest
          export ANDROID_HOME=$HOME/android-sdk
          export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/34.0.0:$PATH
          echo "ANDROID_HOME=$ANDROID_HOME" >> $GITHUB_ENV
          echo "PATH=$PATH" >> $GITHUB_ENV
          yes | $HOME/android-sdk/cmdline-tools/latest/bin/sdkmanager --install "platform-tools" "build-tools;34.0.0"

      - name: Set environment variables
        if: ${{ env.SKIP == 'false' }}
        run: |
          echo "ANDROID_HOME=$HOME/android-sdk" >> $GITHUB_ENV
          echo "ANDROID_SDK_ROOT=$HOME/android-sdk" >> $GITHUB_ENV
          echo "PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/34.0.0:$PATH" >> $GITHUB_ENV

      - name: Install apktool (Fixed)
        if: ${{ env.SKIP == 'false' }}
        run: |
          echo "=== Installing apktool ==="
          # 1. 必要なJavaをインストール
          sudo apt-get update && sudo apt-get install -y openjdk-17-jdk
          
          # 2. 作業ディレクトリにapktoolをダウンロード & インストール（絶対パスを明確に）
          APKTOOL_JAR_PATH="$HOME/apktool.jar"
          APKTOOL_WRAPPER_PATH="$HOME/apktool"
          
          wget -q https://github.com/iBotPeaches/Apktool/releases/download/v2.13.0/apktool_2.13.0.jar -O "$APKTOOL_JAR_PATH"
          
          # 3. ラッパースクリプトを作成 (相対パスではなく絶対パスを使う)
          cat > "$APKTOOL_WRAPPER_PATH" << 'EOF'
          #!/bin/bash
          exec java -jar "$HOME/apktool.jar" "$@"
          EOF
          
          chmod +x "$APKTOOL_WRAPPER_PATH" "$APKTOOL_JAR_PATH"
          
          # 4. ラッパースクリプトをPATHが通った場所に移動
          sudo mv "$APKTOOL_WRAPPER_PATH" /usr/local/bin/
          sudo mv "$APKTOOL_JAR_PATH" /usr/local/bin/
          
          # 5. パスを確認し、グローバルなPATH環境変数に追加
          echo "/usr/local/bin/apktool のインストールを確認:"
          ls -la /usr/local/bin/apktool*
          
          # 現在のセッションと以降のステップのため、PATHを更新
          echo "PATH=/usr/local/bin:$PATH" >> $GITHUB_ENV
          
          echo "=== インストール完了、バージョンチェック ==="
          /usr/local/bin/apktool --version

      - name: Print tool versions
        if: ${{ env.SKIP == 'false' }}
        run: |
          echo "Java version:"
          java -version
          echo "apktool version (full path):"
          /usr/local/bin/apktool --version || echo "Failed to run /usr/local/bin/apktool"
          echo "apktool version (via PATH):"
          apktool --version || echo "'apktool' command not found in PATH"
          echo "aapt2 version:"
          $HOME/android-sdk/build-tools/34.0.0/aapt2 version

      - name: Create downloads directory if not exists
        if: ${{ env.SKIP == 'false' }}
        run: mkdir -p downloads

      - name: Download APK file (with retry and fallback)
        if: ${{ env.SKIP == 'false' }}
        id: download_apk
        continue-on-error: true # Prevents the entire workflow from failing immediately
        run: |
          set -e  # Exit on error for the rest of the commands in this block

          DOWNLOAD_URL="https://github.com/monsivamon/twitter-apk/releases/download/${{ env.monsivamon_TAG }}/twitter-piko-v${{ env.monsivamon_TAG }}.apk"
          OUTPUT_FILE="downloads/twitter-piko-v${{ env.monsivamon_TAG }}.apk"
          MAX_RETRIES=3
          RETRY_DELAY=10

          echo "Attempting to download APK from: $DOWNLOAD_URL"
          echo "Output file: $OUTPUT_FILE"

          # Function to try downloading with curl (more verbose)
          download_with_curl() {
            echo "Attempting download with curl (Attempt $1)..."
            # Use curl with verbose output to see headers, follow redirects, and show errors
            curl -v -L -f "$DOWNLOAD_URL" -o "$OUTPUT_FILE" 2>&1 | tail -20
            return $?
          }

          # Function to try downloading with wget (alternative)
          download_with_wget() {
            echo "Attempting download with wget (Attempt $1)..."
            wget --verbose --tries=1 --timeout=30 "$DOWNLOAD_URL" -O "$OUTPUT_FILE" 2>&1 | tail -10
            return $?
          }

          # Main retry loop
          for ATTEMPT in $(seq 1 $MAX_RETRIES); do
            echo "--- Download Attempt $ATTEMPT of $MAX_RETRIES ---"
            
            # First, try with curl
            if download_with_curl $ATTEMPT; then
              echo "✅ Download successful with curl on attempt $ATTEMPT."
              # Verify the file was downloaded and has content
              if [ -s "$OUTPUT_FILE" ]; then
                echo "✅ File verification passed. Size: $(wc -c < "$OUTPUT_FILE") bytes"
                echo "apk_downloaded=true" >> $GITHUB_ENV
                exit 0  # Success, exit the step
              else
                echo "⚠️  File downloaded but is empty. Retrying..."
                rm -f "$OUTPUT_FILE"
              fi
            else
              echo "❌ curl failed on attempt $ATTEMPT. Exit code: $?"
            fi

            # If curl failed, wait and optionally try wget on the last attempt
            if [ $ATTEMPT -lt $MAX_RETRIES ]; then
              echo "Waiting $RETRY_DELAY seconds before retry..."
              sleep $RETRY_DELAY
            elif [ $ATTEMPT -eq $MAX_RETRIES ]; then
              echo "All curl attempts failed. Trying wget as last resort..."
              if download_with_wget $ATTEMPT; then
                if [ -s "$OUTPUT_FILE" ]; then
                  echo "✅ Wget download successful on final attempt."
                  echo "apk_downloaded=true" >> $GITHUB_ENV
                  exit 0
                fi
              fi
            fi
          done

          # If we get here, all attempts failed
          echo "❌ ERROR: All download attempts failed after $MAX_RETRIES retries."
          echo "Possible issues:"
          echo "1. SAS Token in URL may have expired "
          echo "2. Network connectivity problem"
          echo "3. Release file may not exist at the expected URL"
          echo "Setting status to failed..."
          echo "apk_downloaded=false" >> $GITHUB_ENV
          exit 1  # This will be caught by continue-on-error

      - name: Check APK download and handle failure
        if: ${{ env.SKIP == 'false' }}
        run: |
          echo "Checking APK download result..."
          if [ "${{ env.apk_downloaded }}" == "true" ]; then
            echo "✅ APK download successful. Proceeding with workflow."
            ls -lh downloads/
          else
            echo "❌ APK download failed. The workflow will stop here."
            echo "Please check:"
            echo "1. The monsivamon_TAG: ${{ env.monsivamon_TAG }}"
            echo "2. If the release exists: https://github.com/monsivamon/twitter-apk/releases/tag/${{ env.monsivamon_TAG }}"
            echo "3. If you can manually download the file using a fresh browser session"
            exit 1  # This stops the workflow
          fi

      # The rest of your workflow steps remain the same
      - name: List files in downloads directory
        if: ${{ env.SKIP == 'false' }}
        run: ls -l downloads/

      - name: Run Patch APK script
        if: ${{ env.SKIP == 'false' && env.apk_downloaded == 'true' }}
        run: python patch_apk.py

      - name: Build and sign APK
        if: ${{ env.SKIP == 'false' && env.apk_downloaded == 'true' }}
        run: |
          CLEAN_VERSION=$(echo "${{ env.monsivamon_TAG }}" | sed 's/-release//g')
          echo "Clean version: $CLEAN_VERSION"
          
          INPUT_DIR="decompiled-twitter-$CLEAN_VERSION"
          OUTPUT_DIR="patched_apks"
          KEYSTORE="origin-twitter.keystore"
          ALIAS="origin"
          STOREPASS="123456789"
          KEYPASS="123456789"
          
          if [ ! -d "$INPUT_DIR" ]; then
            echo "Error: Input directory $INPUT_DIR does not exist."
            ls -la
            exit 1
          fi
          
          mkdir -p "$OUTPUT_DIR"
          AAPT2_PATH="$HOME/android-sdk/build-tools/34.0.0/aapt2"
          ZIPALIGN_PATH="$HOME/android-sdk/build-tools/34.0.0/zipalign"
          
          if [ ! -f "$AAPT2_PATH" ]; then
            echo "Error: aapt2 not found at $AAPT2_PATH"
            find $HOME/android-sdk -name aapt2 2>/dev/null || true
            exit 1
          fi
          
          echo "Building APK with apktool..."
          if java -jar /usr/local/bin/apktool.jar b --help 2>&1 | grep -q "use-aapt2"; then
            echo "Using --use-aapt2 option"
            java -jar /usr/local/bin/apktool.jar b "$INPUT_DIR" -o "unsigned.apk" --use-aapt2 "$AAPT2_PATH"
          else
            echo "Using default build (no --use-aapt2 option)"
            java -jar /usr/local/bin/apktool.jar b "$INPUT_DIR" -o "unsigned.apk"
          fi
          
          if [ ! -f "unsigned.apk" ]; then
            echo "Error: Failed to build APK"
            if [ -f "$INPUT_DIR/build/apktool.yml" ]; then
              echo "Checking for error logs..."
              find "$INPUT_DIR" -name "*.log" -exec cat {} \; 2>/dev/null || true
            fi
            exit 1
          fi
          
          if [ ! -f "$KEYSTORE" ]; then
            echo "Creating new keystore..."
            keytool -genkey -v -keystore "$KEYSTORE" -alias "$ALIAS" -keyalg RSA \
              -keysize 2048 -validity 10000 -storepass "$STOREPASS" -keypass "$KEYPASS" \
              -dname "CN=OriginTwitter, OU=Development, O=YuzuMikan404, L=Tokyo, C=JP"
          fi
          
          echo "Signing APK..."
          jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
            -keystore "$KEYSTORE" \
            -storepass "$STOREPASS" \
            -keypass "$KEYPASS" \
            "unsigned.apk" "$ALIAS"
          
          echo "Optimizing APK..."
          "$ZIPALIGN_PATH" -v 4 "unsigned.apk" "$OUTPUT_DIR/twitter-piko-v$CLEAN_VERSION-signed.apk"
          
          if [ -f "$OUTPUT_DIR/twitter-piko-v$CLEAN_VERSION-signed.apk" ]; then
            echo "Build successful! APK saved to: $OUTPUT_DIR/twitter-piko-v$CLEAN_VERSION-signed.apk"
            ls -la "$OUTPUT_DIR/"
          else
            echo "Error: Failed to create signed APK"
            exit 1
          fi

      - name: Run Release APK script
        if: ${{ env.SKIP == 'false' && env.apk_downloaded == 'true' }}
        env:
          GITHUB_TOKEN: ${{ secrets.YuzuMikan404_TOKEN }}
        run: python release_apk.py
