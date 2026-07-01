#!/bin/bash
# 阿里云服务器部署脚本 - 在服务器上执行
set -e

echo "========================================"
echo "  学生成绩管理系统 - 服务器部署"
echo "========================================"

# 1. 检查并安装 Docker
echo ""
echo "[1/5] 检查 Docker..."
if ! command -v docker &> /dev/null; then
    echo "正在安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
fi
echo "  Docker 状态: $(docker --version)"

# 2. 安装 docker compose
echo ""
echo "[2/5] 安装 Docker Compose..."
if ! docker compose version &> /dev/null; then
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
fi
echo "  Compose 状态: OK"

# 3. 克隆项目
echo ""
echo "[3/5] 克隆项目代码..."
if [ -d "grade_system" ]; then
    cd grade_system
    git pull origin master
else
    git clone https://github.com/LYK-0309/grade_system.git
    cd grade_system
fi
echo "  代码已就绪"

# 4. 初始化数据库
echo ""
echo "[4/5] 初始化数据库..."
if [ ! -f "grade_system.db" ]; then
    # 先用 Flask 建表，再导入数据
    docker compose run --rm -T app python -c "
from app import create_app
from app.models import db
app = create_app()
with app.app_context():
    db.create_all()
    print('数据库表已创建')
"
    # 导入初始数据
    docker compose run --rm -T app python init_db.py 2>&1 || echo "  部分导入可能需要手动处理"
else
    echo "  数据库已存在，跳过初始化"
fi

# 5. 启动服务
echo ""
echo "[5/5] 启动服务..."
docker compose down 2>/dev/null || true
docker compose up -d --build

echo ""
echo "========================================"
echo "  ✓ 部署完成！"
echo "  公网访问: http://8.134.154.6"
echo "  超管账号: LYK / lhs623"
echo "========================================"
echo ""
echo "常用命令:"
echo "  查看日志: cd ~/grade_system && docker compose logs -f"
echo "  重启服务: cd ~/grade_system && docker compose restart"
echo "  停止服务: cd ~/grade_system && docker compose down"
