@echo off
rem ============================================================
rem run.bat - 一键启动校园二手交易平台
rem 双击本文件即可启动服务，不用每次手动敲命令
rem ============================================================

rem 切换到项目目录（本文件所在目录）
cd /d %~dp0

rem 激活虚拟环境后启动 uvicorn（--reload 表示改代码自动重启）
call venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

rem 窗口保持打开，方便看日志；按 Ctrl+C 可停止服务
pause
