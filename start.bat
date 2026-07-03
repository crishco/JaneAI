@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [JaneAI] Python virtual environment not found at .venv\Scripts\python.exe
  echo Create it with: python -m venv .venv
  exit /b 1
)

if not exist "node_modules" (
  echo [JaneAI] Installing root Node dependencies...
  call npm install
  if errorlevel 1 exit /b 1
)

if not exist "frontend\node_modules" (
  echo [JaneAI] Installing frontend dependencies...
  call npm --prefix frontend install
  if errorlevel 1 exit /b 1
)

echo [JaneAI] Starting backend, frontend, and Electron...
call npm run start:all
exit /b %ERRORLEVEL%
