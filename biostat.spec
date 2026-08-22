# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para BioStat (onefile, con ventana de carga).

Se construye con `python build_exe.py`, que llama a `pyinstaller biostat.spec`.
Las rutas salen de SPECPATH, asi que el spec funciona en cualquier maquina.
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

PROJECT_DIR = SPECPATH  # noqa: F821 - lo inyecta PyInstaller
SPLASH_IMAGE = os.path.join(PROJECT_DIR, 'assets', 'splash.png')

datas = []
binaries = []
hiddenimports = ['qtawesome', 'scipy.stats', 'scipy.optimize', 'openpyxl', 'reportlab', 'qtpy']

# Paquetes cientificos que necesitan submodulos o datos completos.
# pingouin (ICC/Cronbach) arrastra pandas_flavor/outdated y datos propios.
datas += collect_data_files('statsmodels')
hiddenimports += collect_submodules('statsmodels')
hiddenimports += collect_submodules('sklearn')
hiddenimports += collect_submodules('lifelines')
pingouin_datas, pingouin_binaries, pingouin_hidden = collect_all('pingouin')
datas += pingouin_datas
binaries += pingouin_binaries
hiddenimports += pingouin_hidden


a = Analysis(
    [os.path.join(PROJECT_DIR, 'main.py')],
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Ventana de carga: aparece mientras el onefile se descomprime, antes de que
# corra Python. La linea de estado se actualiza desde src/utils/splash.py.
splash = Splash(
    SPLASH_IMAGE,
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(40, 214),
    text_size=11,
    text_font='Segoe UI',
    text_color='#0e7490',
    text_default='Iniciando BioStat...',
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    a.binaries,
    a.datas,
    [],
    name='BioStat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
