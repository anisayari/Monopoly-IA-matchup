@echo off
echo ========================================
echo    Auto-Launch Toggle for Monopoly IA
echo ========================================
echo.

if exist "config\autolaunch.txt" (
    echo Current status: ENABLED
    echo.
    set /p confirm=Disable auto-launch? (Y/N): 
    if /i "%confirm%"=="Y" (
        del "config\autolaunch.txt"
        echo [OK] Auto-launch disabled
    )
) else (
    echo Current status: DISABLED
    echo.
    set /p confirm=Enable auto-launch? (Y/N): 
    if /i "%confirm%"=="Y" (
        if not exist "config" mkdir "config"
        echo. > "config\autolaunch.txt"
        echo [OK] Auto-launch enabled
        echo.
        echo Dolphin will now start automatically when you run START_MONOPOLY.bat
    )
)

echo.
pause