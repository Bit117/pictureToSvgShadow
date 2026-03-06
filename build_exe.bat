@echo off
REM build_exe.bat - create a Windows executable for the GUI using PyInstaller

REM ensure venv is active or python on PATH
pip install --upgrade pyinstaller
pyinstaller --onefile --windowed app.py

echo Build finished.  Executable should be in dist\app.exe
pause
