import os
import subprocess

# Ruta completa al proyecto y al script a ejecutar
project_path = "/Users/alejandroordonezvillar/Downloads/stock_analyzer_ai"
python_path = "/usr/bin/python3"  # asegúrate de que este es correcto en tu sistema
script_path = os.path.join(project_path, "run_daily.py")

# Línea de cron para ejecutarlo diariamente a las 9:00
cron_line = f"0 9 * * * cd {project_path} && {python_path} run_daily.py >> cron.log 2>&1"

# Obtener crontab actual
try:
    current_crontab = subprocess.check_output(["crontab", "-l"], text=True)
except subprocess.CalledProcessError:
    current_crontab = ""

# Añadir si no existe ya
if cron_line in current_crontab:
    print("✅ La tarea cron ya está configurada.")
else:
    new_crontab = current_crontab.strip() + "\n" + cron_line + "\n"
    process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
    process.communicate(new_crontab.encode())
    print("✅ Tarea cron añadida correctamente.")