@echo off
title Markdown Notes Manager
cls
python app.py
if errorlevel 1 (
    echo.
    echo An error occurred while running Markdown Notes Manager.
    pause
)
