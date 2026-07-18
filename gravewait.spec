# PyInstaller spec: one onedir bundle containing
#   GraveWait.exe       - the game (also --demo / --install-hooks / --uninstall-hooks)
#   gravewait-hook.exe  - tiny fast handler Claude Code's hooks invoke
# Build:  pyinstaller gravewait.spec --noconfirm
# -*- mode: python ; coding: utf-8 -*-

game_a = Analysis(
    ["main.py"],
    pathex=["."],
    datas=[("assets/pack", "assets/pack")],
    hiddenimports=["win32gui", "win32api", "win32con"],
    excludes=["PIL", "tkinter", "numpy"],
)
hook_a = Analysis(
    ["hooks/emit_event.py"],
    pathex=["."],
    excludes=["PIL", "tkinter", "numpy", "pygame"],
)

game_pyz = PYZ(game_a.pure)
hook_pyz = PYZ(hook_a.pure)

game_exe = EXE(
    game_pyz,
    game_a.scripts,
    exclude_binaries=True,
    name="GraveWait",
    icon="installer/gravewait.ico",
    console=False,
)
hook_exe = EXE(
    hook_pyz,
    hook_a.scripts,
    exclude_binaries=True,
    name="gravewait-hook",
    icon="installer/gravewait.ico",
    console=False,
)

COLLECT(
    game_exe,
    game_a.binaries,
    game_a.datas,
    hook_exe,
    hook_a.binaries,
    hook_a.datas,
    name="GraveWait",
)
