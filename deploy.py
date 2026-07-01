"""
阿里云服务器一键部署脚本
通过 SSH 自动登录并部署成绩管理系统
"""
import subprocess
import os
import sys
import tempfile

SERVER_IP = "8.134.154.6"
PASSWORD = "503029448@LYKlyk"

SETUP_SCRIPT = r"""#!/bin/bash
set -e
echo "========================================"
echo "  学生成绩管理系统 - 服务器部署"
echo "========================================"

# 1. 检查 Docker
echo ""
echo "[1/5] 检查 Docker..."
if ! command -v docker &> /dev/null; then
    echo "正在安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
fi
echo "Docker OK: $(docker --version)"

# 2. Docker Compose
echo ""
echo "[2/5] Docker Compose..."
if ! docker compose version &> /dev/null; then
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
fi
echo "Compose OK"

# 3. 克隆项目
echo ""
echo "[3/5] 拉取代码..."
if [ -d "grade_system" ]; then
    cd grade_system && git pull origin master
else
    git clone https://github.com/LYK-0309/grade_system.git && cd grade_system
fi
echo "代码就绪"

# 4. 初始化数据库
echo ""
echo "[4/5] 初始化数据库..."
if [ ! -f "grade_system.db" ]; then
    docker compose run --rm app python -c "
from app import create_app
from app.models import db
app = create_app()
with app.app_context():
    db.create_all()
    print('表创建完成')
"
fi

# 安装 init_db 依赖并初始化
docker compose run --rm app pip install pandas openpyxl -q -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null
docker compose run --rm app python init_db.py 2>&1 || echo "部分数据跳过"

# 5. 启动
echo ""
echo "[5/5] 启动服务..."
docker compose down 2>/dev/null || true
docker compose up -d --build

echo ""
echo "========================================"
echo "  ✓ 部署完成！"
echo "  访问地址: http://8.134.154.6"
echo "  超管: LYK / lhs623"
echo "========================================"
"""

def main():
    print("=" * 50)
    print("  连接服务器 8.134.154.6 ...")
    print("=" * 50)
    
    # 写部署脚本到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, encoding='utf-8') as f:
        f.write(SETUP_SCRIPT)
        script_path = f.name
    
    try:
        # 使用 scp 上传脚本
        print("\n上传部署脚本...")
        scp_cmd = f'scp -o StrictHostKeyChecking=no {script_path} root@{SERVER_IP}:/root/setup.sh'
        
        # 使用 ssh 执行
        print("执行部署（需要输入密码: 503029448@LYKlyk）...")
        ssh_cmd = f'ssh -o StrictHostKeyChecking=no root@{SERVER_IP} "bash /root/setup.sh"'
        
        # 先 scp
        result = subprocess.run(scp_cmd, shell=True, text=True)
        if result.returncode != 0:
            print(f"SCP 失败，请手动操作: {scp_cmd}")
            return
        
        # 再 ssh 执行
        result = subprocess.run(ssh_cmd, shell=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        print("\n部署完成！访问: http://8.134.154.6")
        
    finally:
        os.unlink(script_path)

if __name__ == '__main__':
    main()
