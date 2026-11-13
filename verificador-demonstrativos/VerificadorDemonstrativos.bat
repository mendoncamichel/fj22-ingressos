@echo off
REM Launcher — abre a UI WinForms sem janela de console
setlocal
cd /d "%~dp0"

REM STA é obrigatório para WinForms; -WindowStyle Hidden oculta o console
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -STA -File "%~dp0VerificadorDemonstrativos.ps1"

if errorlevel 1 (
  echo.
  echo Falha ao iniciar o Verificador. Verifique PowerShell 5.1+ e ExecutionPolicy.
  pause
)

endlocal
