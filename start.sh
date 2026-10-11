#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")"

echo "=================================================="
echo " Starting LearnPulse Course Management System"
echo "=================================================="

# 1. Ensure MySQL service is running
echo "Checking MySQL service..."
brew services start mysql > /dev/null 2>&1

# 2. Start Flask Web Server
echo "Starting web server on http://127.0.0.1:5001 ..."
echo ""
echo "Access Modes:"
echo " - Normal Mode:      http://127.0.0.1:5001 (Default: Jack Marston)"
echo " - Instructor Mode:  Password: instructor16"
echo " - Admin Mode:        Password: admin16"
echo ""
echo "Press Ctrl+C to stop the server."
echo "=================================================="

./venv/bin/python app.py
