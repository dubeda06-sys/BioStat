"""Build script para generar el ejecutable de BioStat.

Uso:
    python build_exe.py

Genera BioStat.exe y lo copia al Escritorio del usuario.
"""
import subprocess
import shutil
import os
import sys


def main():
    """Ejecuta PyInstaller y copia el ejecutable al escritorio."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(project_dir, "main.py")

    if not os.path.exists(main_py):
        print("ERROR: No se encontro main.py en el directorio del proyecto.")
        sys.exit(1)

    # Ejecutar PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=BioStat",
        "--hidden-import=qtawesome",
        "--hidden-import=scipy.stats",
        "--hidden-import=scipy.optimize",
        "--hidden-import=sklearn",
        "--hidden-import=statsmodels",
        "--hidden-import=lifelines",
        "--hidden-import=openpyxl",
        "--hidden-import=reportlab",
        "--hidden-import=qtpy",
        main_py,
    ]

    print("Compilando BioStat...")
    result = subprocess.run(cmd, cwd=project_dir)

    if result.returncode != 0:
        print("ERROR: PyInstaller fallo durante la compilacion.")
        sys.exit(1)

    # Ruta del ejecutable generado
    exe_path = os.path.join(project_dir, "dist", "BioStat.exe")

    if not os.path.exists(exe_path):
        print(f"ERROR: No se encontro el ejecutable en {exe_path}")
        sys.exit(1)

    # Copiar al escritorio
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.exists(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Escritorio")

    dest = os.path.join(desktop, "BioStat.exe")
    shutil.copy2(exe_path, dest)
    print(f"Ejecutable copiado exitosamente a: {dest}")
    print("Listo. Puedes ejecutar BioStat desde tu escritorio.")


if __name__ == "__main__":
    main()
