# 腾讯云部署指南

## 概述

本指南帮助您将 zx-card-py 小程序后端 API 部署到腾讯云，包括数据库迁移和服务部署。

## 一、准备工作

### 1.1 本地环境
- Python 3.11+
- Docker（可选）
- 当前 SQLite 数据库（zxcard.db，约 10,413 条数据）

### 1.2 腾讯云服务
需要开通以下服务：
- **云数据库 MySQL**（TencentDB for MySQL）
- **云服务器 CVM** 或 **轻量应用服务器**

---

## 二、配置腾讯云数据库

### 2.1 创建 MySQL 实例

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 搜索"云数据库 MySQL" → 点击"新建"
3. 选择配置：
   - **地域**：选择靠近用户的地区（如广州、上海、北京）
   - **数据库版本**：MySQL 8.0
   - **实例规格**：1核2GB（起步配置）
   - **硬盘**：20GB
   - **网络**：选择 VPC（推荐）
4. 设置 root 密码（务必记住）
5. 完成购买（等待 5-10 分钟初始化）

### 2.2 配置数据库访问

1. 进入实例详情页，记录以下信息：
   - **内网地址**：`xxx.mysql.tencentcdb.com`
   - **端口**：3306
2. 配置安全组规则：
   - 点击"安全组" → "配置安全组"
   - 添加入站规则：MySQL(3306)，允许您的 CVM 内网 IP 段
3. 创建数据库：
   - 使用数据库管理工具或命令行连接
   - 执行：`CREATE DATABASE zxcard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`

---

## 三、数据库迁移

### 3.1 配置迁移脚本

编辑 `export_to_mysql.py` 文件，修改 MySQL 配置：

```python
MYSQL_CONFIG = {
    "host": "your-instance.mysql.tencentcdb.com",  # 替换为您的实例地址
    "port": 3306,
    "user": "root",
    "password": "your_password",  # 替换为您设置的密码
    "database": "zxcard",
    "charset": "utf8mb4",
}
```

### 3.2 执行数据迁移

```bash
# 步骤 1：安装依赖（如果还没有安装）
pip install pymysql

# 步骤 2：测试数据库连接
python export_to_mysql.py --test

# 步骤 3：执行数据迁移
python export_to_mysql.py
# 提示时输入 yes 确认

# 迁移完成后会显示：
# ✓ 导入完成！MySQL 中共有 10413 条记录
```

**注意事项**：
- 此脚本会清空 MySQL 中现有的 cards 表数据
- 确保网络可以访问腾讯云数据库（如需要，配置本地 IP 白名单）
- 数据迁移时间取决于网络速度，约 1-3 分钟

---

## 四、应用部署

### 方案 A：使用 Docker 部署（推荐）

#### 4.1 准备 CVM 服务器

1. 购买云服务器 CVM：
   - 规格：2核4GB（起步配置）
   - 操作系统：Ubuntu 22.04 LTS 或 CentOS 8
   - 带宽：3Mbps 起
2. 配置安全组：
   - 开放端口：22 (SSH)、8000 (API)、80 (HTTP)、443 (HTTPS)

#### 4.2 安装 Docker

```bash
# SSH 登录到服务器后执行：

# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo systemctl start docker
sudo systemctl enable docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 4.3 部署应用

```bash
# 1. 上传代码到服务器
# 方法 1：使用 Git
git clone https://github.com/kll85757/zx-card-py.git
cd zx-card-py

# 方法 2：使用 scp 上传
# scp -r /path/to/zx-card-py root@your-server-ip:/opt/

# 2. 配置环境变量
cp .env.example .env
vim .env  # 编辑配置

# 修改以下内容：
# MYSQL_HOST=your-instance.mysql.tencentcdb.com
# MYSQL_PASSWORD=your_password
# USE_SQLITE=false

# 3. 构建并启动
docker build -t zxcard-api .
docker run -d --name zxcard-api \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  zxcard-api

# 4. 查看日志
docker logs -f zxcard-api
```

### 方案 B：直接部署（不使用 Docker）

```bash
# 1. 安装 Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip -y

# 2. 上传代码并创建虚拟环境
cd /opt/zx-card-py
python3.11 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
vim .env  # 按需修改

# 5. 使用 systemd 管理服务
sudo tee /etc/systemd/system/zxcard-api.service > /dev/null <<'SYSTEMD'
[Unit]
Description=ZXCard API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/zx-card-py
Environment="PATH=/opt/zx-card-py/venv/bin"
ExecStart=/opt/zx-card-py/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD

# 6. 启动服务
sudo systemctl daemon-reload
sudo systemctl start zxcard-api
sudo systemctl enable zxcard-api
sudo systemctl status zxcard-api
```

---

## 五、配置 Nginx 反向代理（可选但推荐）

```bash
# 1. 安装 Nginx
sudo apt install nginx -y

# 2. 配置反向代理
sudo tee /etc/nginx/sites-available/zxcard-api > /dev/null <<'NGINX'
server {
    listen 80;
    server_name your-domain.com;  # 替换为您的域名或 IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

# 3. 启用配置
sudo ln -s /etc/nginx/sites-available/zxcard-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 六、验证和测试

### 6.1 健康检查

```bash
# 测试 API 是否正常
curl http://your-server-ip:8000/health
# 应返回：{"ok":true}

# 测试常量接口
curl http://your-server-ip:8000/api/constants
# 应返回 JSON 格式的常量数据
```

### 6.2 测试搜索功能

```bash
# 搜索卡牌
curl -X POST http://your-server-ip:8000/api/cards/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "红",
    "page_size": 10
  }'
```

### 6.3 小程序配置

在您的微信小程序代码中，将 API 地址修改为：

```javascript
// config.js
const API_BASE_URL = 'http://your-server-ip:8000';
// 或使用域名（需要 HTTPS）
const API_BASE_URL = 'https://your-domain.com';
```

**注意**：微信小程序要求使用 HTTPS，需要：
1. 配置域名
2. 申请 SSL 证书（可使用免费的 Let's Encrypt）
3. 在腾讯云控制台配置 HTTPS

---

## 七、常见问题

### Q1: 数据库连接失败

**问题**：`Can't connect to MySQL server`

**解决方案**：
- 检查安全组是否允许 3306 端口
- 检查 MySQL 实例状态是否正常
- 确认内网地址和密码正确
- 如从本地连接，需要开启公网访问

### Q2: Docker 容器启动失败

**问题**：容器无法启动或频繁重启

**解决方案**：
```bash
# 查看详细日志
docker logs zxcard-api

# 检查环境变量
docker exec zxcard-api env | grep MYSQL

# 进入容器调试
docker exec -it zxcard-api /bin/bash
```

### Q3: API 响应慢

**解决方案**：
- 检查数据库连接池配置
- 考虑添加 Redis 缓存
- 使用 CDN 加速静态资源
- 升级服务器配置

### Q4: 微信小程序无法访问 API

**解决方案**：
- 确保使用 HTTPS（小程序要求）
- 在微信公众平台配置服务器域名白名单
- 检查跨域配置（CORS）

---

## 八、性能优化建议

### 8.1 数据库优化
- 添加索引（已在 export_to_mysql.py 中配置）
- 定期备份数据
- 开启慢查询日志

### 8.2 应用优化
- 启用 Redis 缓存（修改 .env 中的 REDIS_DISABLED=false）
- 使用 Gunicorn 多进程部署
- 配置日志轮转

### 8.3 基础设施优化
- 使用负载均衡（多实例部署）
- 配置 CDN 加速
- 设置监控告警

---

## 九、维护和监控

### 9.1 日志管理

```bash
# Docker 日志
docker logs zxcard-api

# Systemd 服务日志
sudo journalctl -u zxcard-api -f

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 9.2 数据备份

```bash
# MySQL 备份（在腾讯云控制台可设置自动备份）
mysqldump -h your-instance.mysql.tencentcdb.com -u root -p zxcard > backup.sql

# 恢复
mysql -h your-instance.mysql.tencentcdb.com -u root -p zxcard < backup.sql
```

### 9.3 更新部署

```bash
# Docker 方式
cd /opt/zx-card-py
git pull
docker build -t zxcard-api .
docker stop zxcard-api
docker rm zxcard-api
docker run -d --name zxcard-api --env-file .env -p 8000:8000 --restart unless-stopped zxcard-api

# Systemd 方式
cd /opt/zx-card-py
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart zxcard-api
```

---

## 十、成本估算

### 基础版（低流量）
- 云数据库 MySQL 1核2GB：约 ¥100/月
- 云服务器 CVM 2核4GB：约 ¥200/月
- 带宽 3Mbps：约 ¥60/月
- **总计**：约 ¥360/月

### 进阶版（中等流量）
- 云数据库 MySQL 2核4GB：约 ¥300/月
- 云服务器 CVM 4核8GB：约 ¥500/月
- 带宽 10Mbps：约 ¥200/月
- **总计**：约 ¥1000/月

---

## 联系支持

如遇到问题，可参考：
- [腾讯云文档中心](https://cloud.tencent.com/document)
- [腾讯云数据库 MySQL 文档](https://cloud.tencent.com/document/product/236)
- [项目 GitHub Issues](https://github.com/kll85757/zx-card-py/issues)

---

**祝部署顺利！** 🚀
