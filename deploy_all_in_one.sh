#!/bin/bash
#
# Ubuntu 服务器一体化部署脚本
# 包含 MySQL 安装、数据导入、API 部署
#

set -e

echo "========================================"
echo "ZX Card API 一体化部署脚本"
echo "（Ubuntu + MySQL + API）"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查 root 权限
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}错误：需要 root 权限${NC}"
   echo "请使用: sudo bash deploy_all_in_one.sh"
   exit 1
fi

# 设置配置
MYSQL_ROOT_PASSWORD="Zxcard@2024"  # 默认密码，建议修改
MYSQL_DATABASE="zxcard"
APP_DIR="/opt/zx-card-py"
GITHUB_REPO="https://github.com/kll85757/zx-card-py.git"
WECHAT_APPID="wx4387eb448d6892c5"  # 微信小程序 AppID
WECHAT_SECRET=""  # 微信小程序 AppSecret（需要在微信公众平台获取）

echo -e "${BLUE}配置信息：${NC}"
echo "MySQL 密码: ${MYSQL_ROOT_PASSWORD}"
echo "数据库名: ${MYSQL_DATABASE}"
echo "安装目录: ${APP_DIR}"
echo "小程序 AppID: ${WECHAT_APPID}"
echo ""
read -p "继续安装？(y/n): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# ========================================
# 步骤 1: 更新系统
# ========================================
echo ""
echo -e "${GREEN}[1/8] 更新系统...${NC}"
apt update
apt upgrade -y

# ========================================
# 步骤 2: 安装基础工具
# ========================================
echo ""
echo -e "${GREEN}[2/8] 安装基础工具...${NC}"
apt install -y git curl wget vim net-tools

# ========================================
# 步骤 3: 安装 MySQL 8.0
# ========================================
echo ""
echo -e "${GREEN}[3/8] 安装 MySQL 8.0...${NC}"

# 设置 MySQL root 密码（非交互式）
debconf-set-selections <<< "mysql-server mysql-server/root_password password ${MYSQL_ROOT_PASSWORD}"
debconf-set-selections <<< "mysql-server mysql-server/root_password_again password ${MYSQL_ROOT_PASSWORD}"

# 安装 MySQL
apt install -y mysql-server mysql-client

# 启动 MySQL
systemctl start mysql
systemctl enable mysql

# 等待 MySQL 启动
sleep 3

echo -e "${GREEN}✓ MySQL 安装完成${NC}"

# ========================================
# 步骤 4: 配置 MySQL
# ========================================
echo ""
echo -e "${GREEN}[4/8] 配置 MySQL 数据库...${NC}"

# 创建数据库
mysql -uroot -p${MYSQL_ROOT_PASSWORD} <<EOF
CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SHOW DATABASES;
EOF

echo -e "${GREEN}✓ 数据库创建完成${NC}"

# ========================================
# 步骤 5: 安装 Python 3.11
# ========================================
echo ""
echo -e "${GREEN}[5/8] 安装 Python 3.11...${NC}"

# 添加 deadsnakes PPA
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update

# 安装 Python 3.11
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

echo -e "${GREEN}✓ Python 3.11 安装完成${NC}"

# ========================================
# 步骤 6: 下载项目代码
# ========================================
echo ""
echo -e "${GREEN}[6/8] 下载项目代码...${NC}"

if [ -d "$APP_DIR" ]; then
    echo "目录已存在，更新代码..."
    cd "$APP_DIR"
    git pull
else
    git clone ${GITHUB_REPO} ${APP_DIR}
    cd ${APP_DIR}
fi

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ 项目代码准备完成${NC}"

# ========================================
# 步骤 7: 导入数据
# ========================================
echo ""
echo -e "${GREEN}[7/8] 导入卡牌数据...${NC}"

# 检查是否有数据文件
if [ ! -f "zxcard.db" ]; then
    echo -e "${YELLOW}⚠ 警告: 未找到 zxcard.db 文件${NC}"
    echo "请确保项目包含数据库文件，或者稍后手动导入"
else
    # 创建 Python 导入脚本
    cat > /tmp/import_data.py <<'PYEOF'
import sqlite3
import pymysql
import sys

# SQLite 配置
SQLITE_PATH = "zxcard.db"

# MySQL 配置
MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "MYSQL_ROOT_PASSWORD_PLACEHOLDER",
    "database": "MYSQL_DATABASE_PLACEHOLDER",
    "charset": "utf8mb4",
}

print("开始导入数据...")

# 连接数据库
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

mysql_conn = pymysql.connect(**MYSQL_CONFIG)
mysql_cursor = mysql_conn.cursor()

# 创建表
mysql_cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        id INT AUTO_INCREMENT PRIMARY KEY,
        color VARCHAR(16),
        card_number VARCHAR(32),
        series VARCHAR(16),
        rarity VARCHAR(32),
        type VARCHAR(32),
        jp_name VARCHAR(256),
        cn_name VARCHAR(256),
        cost VARCHAR(16),
        power VARCHAR(16),
        race VARCHAR(128),
        note TEXT,
        text_full TEXT,
        image_url VARCHAR(512),
        detail_url VARCHAR(512),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_card_number (card_number),
        INDEX idx_cn_name (cn_name),
        INDEX idx_jp_name (jp_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")
mysql_conn.commit()

# 读取并导入数据
sqlite_cursor.execute("SELECT * FROM cards")
rows = sqlite_cursor.fetchall()
total = len(rows)

print(f"共 {total} 条数据")

sql = """
    INSERT INTO cards (
        color, card_number, series, rarity, type,
        jp_name, cn_name, cost, power, race,
        note, text_full, image_url, detail_url
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

batch_size = 500
for i in range(0, total, batch_size):
    batch = rows[i:i + batch_size]
    values = [
        (r['color'], r['card_number'], r['series'], r['rarity'], r['type'],
         r['jp_name'], r['cn_name'], r['cost'], r['power'], r['race'],
         r['note'], r['text_full'], r['image_url'], r['detail_url'])
        for r in batch
    ]
    mysql_cursor.executemany(sql, values)
    mysql_conn.commit()
    print(f"已导入 {min(i + batch_size, total)}/{total}")

# 验证
mysql_cursor.execute("SELECT COUNT(*) FROM cards")
count = mysql_cursor.fetchone()[0]
print(f"✓ 导入完成！共 {count} 条记录")

mysql_cursor.close()
mysql_conn.close()
sqlite_cursor.close()
sqlite_conn.close()
PYEOF

    # 替换占位符
    sed -i "s/MYSQL_ROOT_PASSWORD_PLACEHOLDER/${MYSQL_ROOT_PASSWORD}/g" /tmp/import_data.py
    sed -i "s/MYSQL_DATABASE_PLACEHOLDER/${MYSQL_DATABASE}/g" /tmp/import_data.py

    # 执行导入
    python /tmp/import_data.py
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 数据导入成功${NC}"
    else
        echo -e "${YELLOW}⚠ 数据导入失败，请检查日志${NC}"
    fi
    
    rm /tmp/import_data.py
fi

# ========================================
# 步骤 8: 配置并启动 API 服务
# ========================================
echo ""
echo -e "${GREEN}[8/8] 配置并启动 API 服务...${NC}"

# 创建 .env 文件
cat > ${APP_DIR}/.env <<EOF
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD}
MYSQL_DB=${MYSQL_DATABASE}
USE_SQLITE=false
MEILI_DISABLED=true
REDIS_DISABLED=true
WECHAT_APPID=${WECHAT_APPID}
WECHAT_SECRET=${WECHAT_SECRET}
EOF

# 创建 systemd 服务
cat > /etc/systemd/system/zxcard-api.service <<EOF
[Unit]
Description=ZXCard API Service
After=network.target mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
ExecStart=${APP_DIR}/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
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
sleep 5

# 检查状态
if systemctl is-active --quiet zxcard-api; then
    echo -e "${GREEN}✓ API 服务启动成功！${NC}"
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    systemctl status zxcard-api
    exit 1
fi

# ========================================
# 测试 API
# ========================================
echo ""
echo -e "${GREEN}测试 API...${NC}"
sleep 2

response=$(curl -s http://localhost:8000/health || echo "failed")
if [[ $response == *"ok"* ]]; then
    echo -e "${GREEN}✓ API 测试成功！${NC}"
    echo "响应: $response"
else
    echo -e "${YELLOW}⚠ API 可能未正常启动${NC}"
fi

# ========================================
# 显示部署信息
# ========================================
echo ""
echo "========================================"
echo -e "${GREEN}部署完成！${NC}"
echo "========================================"
echo ""
echo -e "${BLUE}服务信息：${NC}"
echo "API 地址: http://$(curl -s ifconfig.me):8000"
echo "健康检查: http://$(curl -s ifconfig.me):8000/health"
echo "API 文档: http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo -e "${BLUE}MySQL 信息：${NC}"
echo "主机: 127.0.0.1"
echo "端口: 3306"
echo "用户: root"
echo "密码: ${MYSQL_ROOT_PASSWORD}"
echo "数据库: ${MYSQL_DATABASE}"
echo ""
echo -e "${BLUE}常用命令：${NC}"
echo "查看服务状态: sudo systemctl status zxcard-api"
echo "查看日志: sudo journalctl -u zxcard-api -f"
echo "重启服务: sudo systemctl restart zxcard-api"
echo "停止服务: sudo systemctl stop zxcard-api"
echo ""
echo -e "${BLUE}微信小程序配置：${NC}"
echo "AppID: ${WECHAT_APPID}"
echo "AppSecret: 需要在微信公众平台获取"
echo ""
echo -e "${YELLOW}下一步（重要）：${NC}"
echo "1. 配置防火墙: sudo ufw allow 8000/tcp && sudo ufw enable"
echo "2. 申请域名并配置 DNS 解析到服务器 IP"
echo "3. 配置 HTTPS 证书（微信小程序强制要求）"
echo "4. 在微信公众平台配置服务器域名白名单"
echo "5. 获取并配置小程序 AppSecret（.env 文件）"
echo ""
echo -e "${BLUE}微信小程序后台配置：${NC}"
echo "访问: https://mp.weixin.qq.com"
echo "路径: 开发管理 → 开发设置"
echo "  - 获取 AppSecret（首次需生成）"
echo "  - 配置 request 合法域名: https://your-domain.com"
echo "  - 注意：必须使用 HTTPS，不支持 HTTP 和 IP 地址"
echo ""
echo -e "${YELLOW}注意事项：${NC}"
echo "- 微信小程序要求必须使用 HTTPS"
echo "- 默认 MySQL 密码建议修改"
echo "- 建议使用腾讯云 MySQL（生产环境）"
echo "- 定期备份数据库"
echo "- 查看完整对接指南: WECHAT_MINIPROGRAM_GUIDE.md"
echo ""
