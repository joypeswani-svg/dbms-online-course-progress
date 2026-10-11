#!/bin/bash

# Navigate to the directory containing this script
cd "$(dirname "$0")"

echo "=================================================="
echo " Starting LearnPulse Course Management System..."
echo "=================================================="

# 1. Start MySQL service if not already running
brew services start mysql > /dev/null 2>&1

# 2. Wait 1.5 seconds then open the web app automatically in your default browser
(sleep 1.5 && open "http://127.0.0.1:5001") &

echo "Opening http://127.0.0.1:5001 in your browser..."
echo ""
echo "Access Passwords:"
echo " - Instructor Mode: instructor16"
echo " - Admin Mode:      admin16"
echo ""
echo "Keep this window open while using the app."
echo "Close this window or press Ctrl+C when you want to stop."
echo "=================================================="

# 3. Launch the Python Flask server
./venv/bin/python app.py
