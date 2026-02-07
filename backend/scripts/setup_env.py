"""Script para copiar .env.example a .env"""
import shutil
import os

env_example = ".env.example"
env_file = ".env"

if not os.path.exists(env_file):
    shutil.copy(env_example, env_file)
    print(f"✓ Archivo {env_file} creado desde {env_example}")
    print(f"  Edita {env_file} con tus configuraciones antes de ejecutar.")
else:
    print(f"✗ {env_file} ya existe, no se sobrescribirá")
