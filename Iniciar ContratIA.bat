@echo off
REM ============================================================
REM ContratIA v2.0 - Inicializador Automatico
REM ============================================================

echo.
echo ============================================================
echo   Iniciando ContratIA v2.0...
echo ============================================================
echo.

REM Navegar para pasta do projeto
cd /d "%~dp0"

REM Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale Python 3.7+ primeiro.
    pause
    exit /b 1
)

REM Verificar dependencias
echo [1/3] Verificando dependencias...
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Instalando dependencias...
    pip install -r requirements.txt
)

echo [2/3] Abrindo navegador automaticamente...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5000

echo [3/3] Iniciando servidor web...
echo.
echo ============================================================
echo   ContratIA v2.0 esta RODANDO!
echo ============================================================
echo   Acesse: http://127.0.0.1:5000
echo.
echo   Para PARAR o servidor: Pressione Ctrl+C
echo ============================================================
echo.

REM Iniciar servidor Flask
python app_v2.py

REM Se o servidor parar, pausar para ver mensagens de erro
pause
