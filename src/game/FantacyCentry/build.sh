#!/bin/bash
# Build script for Linux (testing)
echo "Building FantacyCentry..."

pyinstaller --onefile --windowed \
    --name "FantacyCentry" \
    --add-data "data:data" \
    --add-data "assets:assets" \
    main.py

echo "Build complete! Check dist/ folder."
