@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo [信息] 正在构建应用程序...

:: 设置工作目录为脚本所在目录
cd /d "%~dp0"

:: 清理旧文件
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "*.spec" del /f /q "*.spec"

:: 生成图标
echo [信息] 正在生成图标...
python create_icon.py
if !errorlevel! neq 0 (
    echo [错误] 图标生成失败！
    pause
    exit /b 1
)

:: 打包程序
echo [信息] 正在打包程序...
python -m PyInstaller ^
--noconsole ^
--onefile ^
--icon="cleaner.ico" ^
--add-data "cleaner.ico;." ^
--name="吓吓C盘" ^
"windows_c_clean.py"

:: 等待一下确保文件写入完成
timeout /t 2 >nul

:: 设置输出路径
set "OUTPUT_EXE=%~dp0dist\吓吓C盘.exe"

:: 检查打包结果
echo [信息] 检查生成的文件...
dir "!OUTPUT_EXE!" >nul 2>&1
if !errorlevel! neq 0 (
    echo [错误] 程序打包失败！
    echo [信息] 请检查 build\吓吓C盘\warn-吓吓C盘.txt 文件查看详细错误信息
    pause
    exit /b 1
)

:: 编译安装程序
set "INNO_SETUP=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "CHINESE_ISL=C:\Program Files (x86)\Inno Setup 6\Languages\ChineseSimplified.isl"

:: 检查 Inno Setup
echo [信息] 检查 Inno Setup...
dir "!INNO_SETUP!" >nul 2>&1
if !errorlevel! neq 0 (
    echo [错误] 未找到 Inno Setup，请先安装 Inno Setup 6
    echo 下载地址：https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

:: 检查中文语言包
echo [信息] 检查中文语言包...
dir "!CHINESE_ISL!" >nul 2>&1
if !errorlevel! neq 0 (
    echo [错误] 未找到中文语言包，请先安装 Inno Setup 中文语言包
    echo 下载地址：https://jrsoftware.org/files/istrans/
    pause
    exit /b 1
)

:: 生成安装程序
echo [信息] 正在生成安装程序...
"!INNO_SETUP!" "setup.iss"
if !errorlevel! neq 0 (
    echo [错误] 安装程序生成失败！
    pause
    exit /b 1
)

echo.
echo =====================
echo   构建成功完成！
echo =====================
echo.
pause 