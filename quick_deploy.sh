#!/bin/bash
#
# 腾讯云快速部署脚本
# 用于在 CVM 服务器上快速部署 zx-card-py 项目
#

set -e

echo "=================================="
echo "ZX Card API 腾讯云部署脚本"
echo "=================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}错误：此脚本需要 root 权限运行${NC}"
   echo "请使用: sudo bash quick_deploy.sh"
   exit 1
fi

# 询问部署方式
echo "请选择部署方式："
echo "1) Docker 部署（推荐）"
echo "2) 直接部署（使用 systemd）"
read -p "请输入选项 [1/2]: " deploy_method

# 询问 MySQL 配置
echo ""
echo -e "${YELLOW}请输入腾讯云 MySQL 配置：${NC}"
read -p "MySQL 主机地址: " mysql_host
read -p "MySQL 端口 [3306]: " mysql_port
mysql_port=${mysql_port:-3306}
read -p "MySQL 用户名 [root]: " mysql_user
mysql_user=${mysql_user:-root}
read -sp "MySQL 密码: " mysql_password
echo ""
read -p "MySQL 数据库名 [zxcard]: " mysql_db
mysql_db=${mysql_db:-zxcard}

# 询问项目目录
read -p "项目安装目录 [/opt/zx-card-py]: " install_dir
install_dir=${install_dir:-/opt/zx-card-py}

echo ""
echo -e "${GREEN}配置确认：${NC}"
echo "部署方式: $deploy_method"
echo "MySQL 主机: $mysql_host"
echo "MySQL 端口: $mysql_port"
echo "MySQL 用户: $mysql_user"
echo "MySQL 数据库: $mysql_db"
echo "安装目录: $install_dir"
echo ""
read -p "确认继续？[y/N]: " confirm

if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "已取消部署"
    exit 0
fi

# 更新系统
echo ""
echo -e "${GREEN}[1/6] 更新系统...${NC}"
apt update && apt upgrade -y

# 安装基础工具
echo ""
echo -e "${GREEN}[2/6] 安装基础工具...${NC}"
apt install -y git curl vim wget net-tools

if [ "$deploy_method" == "1" ]; then
    # Docker 部署
    echo ""
    echo -e "${GREEN}[3/6] 安装 Docker...${NC}"
    
    # 检查 Docker 是否已安装
    if command -v docker &> /dev/null; then
        echo "Docker 已安装，跳过安装步骤"
    else
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl start docker
        systemctl enable docker
        rm get-docker.sh
    fi
    
    # 下载项目
    echo ""
    echo -e "${GREEN}[4/6] 下载项目代码...${NC}"
    if [ -d "$install_dir" ]; then
        echo "目录已存在，更新代码..."
        cd "$install_dir"
        git pull
    else
        git clone https://github.com/kll85757/zx-card-py.git "$install_dir"
        cd "$install_dir"
    fi
    
    # 创建 .env 文件
    echo ""
    echo -e "${GREEN}[5/6] 配置环境变量...${NC}"
    cat > .env <<EOF
MYSQL_HOST=$mysql_host
MYSQL_PORT=$mysql_port
MYSQL_USER=$mysql_user
MYSQL_PASSWORD=$mysql_password
MYSQL_DB=$mysql_db
USE_SQLITE=false
MEILI_DISABLED=true
REDIS_DISABLED=true
EOF
    
    # 构建并启动
    echo ""
    echo -e "${GREEN}[6/6] 构建并启动服务...${NC}"
    
    # 停止旧容器
    docker stop zxcard-api 2>/dev/null || true
    docker rm zxcard-api 2>/dev/null || true
    
    # 构建镜像
    docker build -t zxcard-api .
    
    # 启动容器
    docker run -d \
        --name zxcard-api \
        --env-file .env \
        -p 8000:8000 \
        --restart unless-stopped \
        zxcard-api
    
    # 等待启动
    echo "等待服务启动..."
    sleep 5
    
    # 检查状态
    if docker ps | grep -q zxcard-api; then
        echo -e "${GREEN}✓ 服务启动成功！${NC}"
        echo ""
        echo "查看日志: docker logs -f zxcard-api"
        echo "停止服务: docker stop zxcard-api"
        echo "重启服务: docker restart zxcard-api"
    else
        echo -e "${RED}✗ 服务启动失败，请查看日志${NC}"
        docker logs zxcard-api
        exit 1
    fi
    
else
    # 直接部署
    echo ""
    echo -e "${GREEN}[3/6] 安装 Python 3.11...${NC}"
    apt install -y python3.11 python3.11-venv python3-pip
    
    # 下载项目
    echo ""
    echo -e "${GREEN}[4/6] 下载项目代码...${NC}"
    if [ -d "$install_dir" ]; then
        echo "目录已存在，更新代码..."
        cd "$install_dir"
        git pull
    else
        git clone https://github.com/kll85757/zx-card-py.git "$install_dir"
        cd "$install_dir"
    fi
    
    # 创建虚拟环境
    echo "创建虚拟环境..."
    python3.11 -m venv venv
    source venv/bin/activate
    
    # 安装依赖
    echo "安装依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 创建 .env 文件
    echo ""
    echo -e "${GREEN}[5/6] 配置环境变量...${NC}"
    cat > .env <<EOF
MYSQL_HOST=$mysql_host
MYSQL_PORT=$mysql_port
MYSQL_USER=$mysql_user
MYSQL_PASSWORD=$mysql_password
MYSQL_DB=$mysql_db
USE_SQLITE=false
MEILI_DISABLED=true
REDIS_DISABLED=true
EOF
    
    # 创建 systemd 服务
    echo ""
    echo -e "${GREEN}[6/6] 配置 systemd 服务...${NC}"
    cat > /etc/systemd/system/zxcard-api.service <<EOF
[Unit]
Description=ZXCard API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$install_dir
Environment="PATH=$install_dir/venv/bin"
ExecStart=$install_dir/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # 启动服务
    systemctl daemon-reload
    systemctl stop zxcard-api 2>/dev/null || true
    systemctl start zxcard-api
    systemctl enable zxcard-api
    
    # 等待启动
    echo "等待服务启动..."
    sleep 3
    
    # 检查状态
    if systemctl is-active --quiet zxcard-api; then
        echo -e "${GREEN}✓ 服务启动成功！${NC}"
        echo ""
        echo "查看日志: sudo journalctl -u zxcard-api -f"
        echo "查看状态: sudo systemctl status zxcard-api"
        echo "停止服务: sudo systemctl stop zxcard-api"
        echo "重启服务: sudo systemctl restart zxcard-api"
    else
        echo -e "${RED}✗ 服务启动失败，请查看日志${NC}"
        journalctl -u zxcard-api -n 50
        exit 1
    fi
fi

# 测试 API
echo ""
echo -e "${GREEN}测试 API...${NC}"
sleep 2
response=$(curl -s http://localhost:8000/health)
if [[ $response == *"ok"* ]]; then
    echo -e "${GREEN}✓ API 测试成功！${NC}"
    echo "响应: $response"
else
    echo -e "${YELLOW}⚠ API 可能未正常启动，请检查${NC}"
fi

# 显示访问信息
echo ""
echo "=================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=================================="
echo ""
echo "API 地址: http://$(curl -s ifconfig.me):8000"
echo "健康检查: http://$(curl -s ifconfig.me):8000/health"
echo "API 文档: http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "下一步："
echo "1. 配置防火墙开放 8000 端口"
echo "2. 配置 Nginx 反向代理（可选）"
echo "3. 配置 HTTPS 证书（微信小程序必需）"
echo "4. 在小程序中配置 API 地址"
echo ""
echo "详细文档请参考: DEPLOY_TO_TENCENT_CLOUD.md"
echo ""
