rem chcp 65001
@echo off 
set /p pwds="please input password:"
if "%pwds%"== "stopservice"   ( venv\Scripts\python.exe main.py action-stop.yaml )  else  (echo "password wrong!")
cmd