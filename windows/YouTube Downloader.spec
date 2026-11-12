# -*- mode: python ; coding: utf-8 -*-
# YouTube Downloader 3.x - pywebview (Edge WebView2) UI + yt-dlp + ffmpeg.
# Build (from this folder):
#   C:\Users\70463\ai-music-deconstructor-windows\.venv\Scripts\pyinstaller.exe --noconfirm "YouTube Downloader.spec"
from PyInstaller.utils.hooks import collect_all

datas = [('app_icon.ico', '.'), ('ui', 'ui'), ('ffmpeg/ffmpeg.exe', 'ffmpeg')]
binaries = []
hiddenimports = ['clr', 'webview.platforms.winforms', 'webview.platforms.edgechromium']
for pkg in ('webview', 'yt_dlp', 'clr_loader', 'pythonnet'):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

a = Analysis(
    ['yt_downloader.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'numpy', 'torchaudio', 'demucs', 'onnxruntime', 'tkinter', 'PIL', 'matplotlib', 'scipy', 'onnx', 'pytest', 'IPython', 'customtkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='YouTube Downloader',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
    icon='app_icon.ico',
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[], name='YouTube Downloader')
