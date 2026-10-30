@echo off
title ReturnFlow - FastAPI Server & Web Portal
echo =====================================================================
echo  ReturnFlow - Reusable Asset Return & Lifecycle Management System
echo  Serving API and Web Portal on http://127.0.0.1:8000
echo =====================================================================
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
