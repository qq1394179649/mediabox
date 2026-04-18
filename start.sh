#!/bin/bash
# Emby管理系统 - Linux/Mac启动脚本

echo "============================================"
echo "   Emby 管理系统 - 启动脚本"
echo "============================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装"
    exit 1
fi

echo "[1/3] 检查依赖..."
if ! python3 -c "import flask" &> /dev/null; then
    echo "[安装] 正在安装依赖包..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
else
    echo "[OK] 依赖已就绪"
fi

echo ""
echo "[2/3] 检查配置..."
if [ ! -f .env ]; then
    echo "[警告] 未找到.env配置文件"
    cp .env.example .env
    echo "[OK] 已创建.env文件，请编辑后重新启动"
    exit 0
fi
echo "[OK] 配置文件已就绪"

echo ""
echo "[3/3] 启动服务..."
echo ""
echo "============================================"
echo " 访问地址: http://localhost:5000"
echo " 按 Ctrl+C 停止服务"
echo "============================================"
echo ""

python3 app.py
