@echo off
cd C:\Users\flavi\Desktop\syko-cinema

start cmd /k python main.py
timeout /t 5 >nul
start cmd /k ngrok http 8080
