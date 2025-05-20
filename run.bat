@echo off
start cmd /k "cd /d %~dp0 && python -m uvicorn api:app --reload"
start cmd /k "cd /d %~dp0 && python main.py"