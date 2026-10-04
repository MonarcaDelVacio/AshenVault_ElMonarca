@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo        AshenVault - Iniciando
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en PATH.
    echo Instala Python 3.11+ y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

echo Instalando/comprobando dependencias...
echo.
python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudieron instalar las dependencias.
    echo Ejecuta este archivo desde una consola para ver el error completo.
    echo.
    pause
    exit /b 1
)

echo Dependencias instaladas. Ejecutando comprobacion de la intro...
echo.
python check_intro.py
if errorlevel 1 (
    echo.
    echo [ERROR] La comprobacion de intro.mp4 fallo. El juego no se iniciara para evitar saltar la intro silenciosamente.
    echo Revisa el error mostrado arriba.
    echo.
    pause
    exit /b 1
)
echo.
echo [OK] Intro validada. Iniciando AshenVault...
echo.
python main.py
set EXITCODE=%ERRORLEVEL%

echo.
if not "%EXITCODE%"=="0" (
    echo [ERROR] AshenVault termino con codigo %EXITCODE%.
)
pause
exit /b %EXITCODE%
