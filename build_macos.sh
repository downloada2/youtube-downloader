#!/usr/bin/env bash
# Builds "YouTube Downloader.app" and "YouTube Downloader.dmg" on macOS.
# Run this ON the Mac - PyInstaller cannot cross-compile from Windows.
# (GitHub Actions does exactly this for Apple Silicon and Intel.)
#
#   chmod +x build_macos.sh
#   ./build_macos.sh
#
# The window is a native WKWebView (pywebview) - no Tk needed. The result is
# native for the Mac that built it: Apple Silicon -> arm64, Intel -> x86_64.
set -euo pipefail
cd "$(dirname "$0")"
NAME="YouTube Downloader"

echo "== Creating virtual environment (.venv) =="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install yt-dlp imageio-ffmpeg pyinstaller pywebview

echo "== Building $NAME.app =="
pyinstaller --noconfirm --clean --windowed --name "$NAME" \
    --icon "$PWD/app_icon.icns" --osx-bundle-identifier com.ytdl.downloader \
    --add-data "$PWD/ui:ui" \
    --collect-all yt_dlp --collect-all imageio_ffmpeg --collect-all webview \
    --exclude-module tkinter \
    --distpath dist --workpath build --specpath build \
    yt_downloader.py
codesign --force --deep --sign - "dist/$NAME.app" || true

echo "== Making $NAME.dmg =="
rm -rf dist/dmg && mkdir -p dist/dmg
cp -R "dist/$NAME.app" dist/dmg/
ln -s /Applications dist/dmg/Applications
hdiutil create -volname "$NAME" -srcfolder dist/dmg -ov -format UDZO "dist/$NAME.dmg"
rm -rf dist/dmg

echo
echo "Done: dist/$NAME.dmg - open it and drag the app into Applications."
echo "First launch: the app isn't notarized, so macOS says 'unidentified"
echo "developer' - right-click the app -> Open -> Open, once."
