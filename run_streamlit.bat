@echo off
cd /d "%~dp0"
call backend\venv\Scripts\activate
set PYTHONPATH=%CD%\backend
streamlit run streamlit_app.py
pause
