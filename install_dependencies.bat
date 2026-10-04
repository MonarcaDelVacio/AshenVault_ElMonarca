@echo off
setlocal
cd /d "%~dp0"
echo Instalando dependencias de AshenVault...
echo.
python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] La instalacion fallo.
    pause
    exit /b 1
)
echo.
echo Instalacion completada correctamente.
echo.
python -c "import pygame, av; print('Pygame OK'); print('PyAV:', av.__version__)"
echo.
pause
