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
    spec = os.path.join(project_dir, "biostat.spec")
    splash_png = os.path.join(project_dir, "assets", "splash.png")

    if not os.path.exists(main_py):
        print("ERROR: No se encontro main.py en el directorio del proyecto.")
        sys.exit(1)

    if not os.path.exists(spec):
        print(f"ERROR: No se encontro la receta {spec}")
        sys.exit(1)

    # La imagen de la ventana de carga se versiona en el repo; si falta, se
    # regenera antes de compilar (el spec la exige).
    if not os.path.exists(splash_png):
        print("Falta assets/splash.png; regenerandola...")
        gen = subprocess.run(
            [sys.executable, os.path.join(project_dir, "scripts", "make_splash.py")],
            cwd=project_dir,
        )
        if gen.returncode != 0 or not os.path.exists(splash_png):
            print("ERROR: No se pudo generar la imagen de la ventana de carga.")
            sys.exit(1)

    # Compilar desde el spec: ahi viven los hidden imports, los collect_all de
    # los paquetes cientificos y la configuracion del splash.
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        spec,
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

    # Copiar al escritorio (soporta OneDrive y localizaciones ES/EN)
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Escritorio"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "OneDrive", "Escritorio"),
    ]
    desktop = next((d for d in candidates if os.path.isdir(d)), None)

    if desktop is None:
        print(f"AVISO: no se encontro el Escritorio. El ejecutable esta en: {exe_path}")
        return

    dest = os.path.join(desktop, "BioStat.exe")
    shutil.copy2(exe_path, dest)
    print(f"Ejecutable copiado exitosamente a: {dest}")
    print("Listo. Puedes ejecutar BioStat desde tu escritorio.")


if __name__ == "__main__":
    main()
