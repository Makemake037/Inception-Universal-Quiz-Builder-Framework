@echo off
echo 🚀 Starting Inception Quiz Server...
start http://localhost:8000/spawn.html
python -m http.server 8000
pause