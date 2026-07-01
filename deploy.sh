#!/bin/bash
# 学生成绩管理系统 - 阿里云一键部署脚本
# 用法: chmod +x deploy.sh && ./deploy.sh

set -e

echo "========================================"
echo "  学生成绩管理系统 - 阿里云部署"
echo "========================================"

# 1. 更新系统
echo "[1/5] 更新系统包..."
sudo apt-get update -y && sudo apt-get upgrade -y

# 2. 安装 Docker
echo "[2/5] 安装 Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo bash
    sudo usermod -aG docker $USER
    echo "Docker 安装完成，请重新登录或执行: newgrp docker"
fi

# 3. 安装 Docker Compose
echo "[3/5] 安装 Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    sudo apt-get install -y docker-compose-plugin
fi

# 4. 初始化数据库（首次运行）
echo "[4/5] 初始化数据库..."
if [ ! -f grade_system.db ]; then
    sudo docker compose run --rm app python init_db.py || true
    echo "数据库初始化完成"
else
    echo "数据库已存在，跳过初始化"
fi

# 5. 启动服务
echo "[5/5] 启动服务..."
sudo docker compose up -d --build

echo ""
echo "========================================"
echo "  部署完成！"
echo "  访问地址: http://$(curl -s ifconfig.me)"
echo "========================================"
echo ""
echo "常用命令:"
echo "  查看日志: docker compose logs -f"
echo "  重启服务: docker compose restart"
echo "  停止服务: docker compose down"
echo "  重新构建: docker compose up -d --build"
