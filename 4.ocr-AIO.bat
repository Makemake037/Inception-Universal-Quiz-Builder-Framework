@echo off
:: 1. Move to the directory where this batch file lives
cd /d "%~dp0"

:: 2. Intelligently look for the 'quizenv' virtual environment one step back (parent dir) or locally
if exist "..\quizenv\Scripts\activate.bat" (
    call "..\quizenv\Scripts\activate.bat"
    echo 📂 [INFO]: Found 'quizenv' in parent directory.
) else if exist "quizenv\Scripts\activate.bat" (
    call "quizenv\Scripts\activate.bat"
    echo 📂 [INFO]: Found 'quizenv' in current directory.
) else (
    echo ❌ [ERROR]: Could not find 'quizenv' virtual environment!
    echo Please make sure 0.setup_env.py has been run in the root folder.
    pause
    exit /b
)

:: 3. Run target Python script seamlessly
echo 🚀 Running OCR Application via isolated environment...
python 4.ocr-AIO.py

pause