@echo off
REM bootstrap.bat - double-clickable Windows launcher for setup.sh.
REM setup.sh is a bash script, so this runs it via Git Bash.
setlocal
cd /d "%~dp0"

REM Prefer bash on PATH (Git Bash), then fall back to common install locations.
where bash >nul 2>nul
if %ERRORLEVEL%==0 (
    bash setup.sh
    goto :end
)
if exist "%ProgramFiles%\Git\bin\bash.exe" (
    "%ProgramFiles%\Git\bin\bash.exe" setup.sh
    goto :end
)
if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" (
    "%ProgramFiles(x86)%\Git\bin\bash.exe" setup.sh
    goto :end
)

echo ERROR: Git Bash was not found.
echo Install Git for Windows (which includes Git Bash), then run this again,
echo or run "bash setup.sh" from a Git Bash terminal.

:end
echo.
pause
