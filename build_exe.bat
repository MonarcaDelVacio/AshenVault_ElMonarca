@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo        AshenVault - Build EXE
echo ========================================
echo.

echo Instalando/comprobando dependencias (incluye PyAV)...
python -m pip install --disable-pip-version-check -r requirements.txt pyinstaller
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudieron instalar las dependencias.
    pause
    exit /b 1
)

echo.
echo Ejecutando comprobacion de la intro...
python check_intro.py
if errorlevel 1 (
    echo.
    echo [ERROR] La comprobacion de intro.mp4 fallo. No se continuara con el build.
    pause
    exit /b 1
)
echo [OK] Intro validada.
echo.

if exist "assets\icons\AshenVaultIcon.ico" goto BUILD_WITH_ICON

echo [AVISO] No se encontro AshenVaultIcon.ico.
echo Se generara el ejecutable sin icono de Windows.
echo.
echo Construyendo AshenVault.exe...
python -m PyInstaller --noconfirm --onefile --windowed --name AshenVault --add-data "data;data" --add-data "assets;assets" --collect-all av --collect-all numpy main.py
goto CHECK_RESULT

:BUILD_WITH_ICON
echo Icono encontrado: assets\icons\AshenVaultIcon.ico
echo.
echo Construyendo AshenVault.exe con icono...
python -m PyInstaller --noconfirm --onefile --windowed --name AshenVault --icon "assets\icons\AshenVaultIcon.ico" --add-data "data;data" --add-data "assets;assets" --collect-all av --collect-all numpy main.py

:CHECK_RESULT
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller no pudo generar el ejecutable.
    echo Revisa el mensaje anterior para ver la causa.
    pause
    exit /b 1
)

echo.
echo ========================================
echo EJECUTABLE GENERADO CORRECTAMENTE
echo.
echo Ubicacion:
echo %~dp0dist\AshenVault.exe
echo ========================================
echo.
pause
exit /b 0
