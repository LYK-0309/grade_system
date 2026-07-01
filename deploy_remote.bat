@echo off
chcp 65001 >nul
echo ==========================================
echo   学生成绩管理系统 - 一键部署
echo   目标服务器: 8.134.154.6
echo ==========================================
echo.
echo 接下来会提示输入密码: 503029448@LYKlyk
echo 输入后按回车（输入时不会显示字符，正常现象）
echo.

ssh -o StrictHostKeyChecking=no root@8.134.154.6 "bash -s" < %~dp0server_setup.sh

echo.
echo ==========================================
echo   部署完成！
echo   访问: http://8.134.154.6
echo ==========================================
pause
