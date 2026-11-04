@echo off
echo ==========================================================
echo  Starting JARVIS AI Justice Access ^& Navigation System
echo  Developer: Divyesh Bambhaniya
echo ==========================================================

cd backend
echo Installing backend requirements...
pip install -r requirements.txt
start python main.py

cd ..\frontend
echo Starting Frontend Web App...
start index.html
