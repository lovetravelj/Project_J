@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=utf-8
set PYTHON=C:\Users\usejen_id\Documents\Project_J\.venv\Scripts\python.exe
"%PYTHON%" -X utf8 -m streamlit run app.py
