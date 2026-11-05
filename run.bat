@echo off
cd /d C:\Users\kokka\Projects\domx-kotsovolos-plaisio
call .venv\Scripts\activate.bat
if not exist logs mkdir logs
echo ===== %date% %time% ===== >> logs\run.log
python main.py >> logs\run.log 2>&1