@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo      AshenVault - Build Setup
echo ========================================
echo.

where ISCC.exe >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encontro Inno Setup Compiler (ISCC.exe).
    echo Instala Inno Setup 6 en la PC de desarrollo y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)

if not exist "dist\AshenVault.exe" (
    echo [ERROR] No existe dist\AshenVault.exe.
    echo Ejecuta primero build_exe.bat.
    pause
    exit /b 1
)

if not exist "assets\icons\AshenVaultIcon.ico" (
    echo [ERROR] No existe assets\icons\AshenVaultIcon.ico.
    pause
    exit /b 1
)

if not exist "installer" mkdir installer
ISCC.exe "AshenVault_Setup.iss"
if errorlevel 1 (
    echo.
    echo [ERROR] Inno Setup no pudo generar el instalador.
    pause
    exit /b 1
)

echo.
echo ========================================
echo SETUP GENERADO CORRECTAMENTE
echo.
echo Ubicacion:
echo %~dp0installer\AshenVault_Setup.exe
echo ========================================
echo.
pause
exit /b 0
