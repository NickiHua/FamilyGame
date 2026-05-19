@echo off
echo Building FantacyCentry for Windows...
echo.
echo Make sure you have conda env 'game' activated:
echo   conda activate game
echo   pip install pyinstaller
echo.

pyinstaller --onefile --windowed ^
    --name "幻世纪" ^
    --add-data "data;data" ^
    --add-data "assets;assets" ^
    main.py

echo.
echo Build complete! Check dist/ folder.
pause
