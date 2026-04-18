@echo off
chcp 65001 >nul
echo ============================================
echo    Emby 管理系统 - 启动脚本
echo ============================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查pip配置
        pause
        exit /b 1
    )
) else (
    echo [OK] 依赖已就绪
)

echo.
echo [2/3] 检查配置...
if not exist .env (
    echo [警告] 未找到.env配置文件，使用默认配置
    copy .env.example .env
    echo [OK] 已从模板创建.env文件，请编辑后重新启动
    echo.
    echo 请编辑 .env 文件，配置以下参数：
    echo   EMBY_SERVER_URL  - Emby服务器地址
    echo   EMBY_API_KEY     - Emby API密钥
    echo   ADMIN_USERNAME   - 管理面板用户名
    echo   ADMIN_PASSWORD   - 管理面板密码
    pause
    exit /b 0
)

echo [OK] 配置文件已就绪
echo.
echo [3/3] 启动服务...
echo.
echo ============================================
echo  访问地址: http://localhost:5000
echo  按 Ctrl+C 停止服务
echo ============================================
echo.

python app.py
pause
