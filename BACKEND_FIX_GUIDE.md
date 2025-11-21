# 后端 500 错误修复指南

## 问题描述

搜索接口 `POST /api/cards/search` 返回 500 Internal Server Error

**测试请求：**
```json
{
  "colors": ["白"],
  "page_size": 50
}
```

**错误状态码：** 500

---

## 快速修复步骤

### 步骤 1：查看服务器日志

SSH 登录服务器并查看详细错误日志：

```bash
# 查看最新日志
sudo journalctl -u zxcard-api -n 100 --no-pager

# 实时监控日志
sudo journalctl -u zxcard-api -f
```

记录具体的错误信息。

### 步骤 2：更新代码

代码已更新（添加了详细错误日志），需要重新部署：

```bash
# 进入项目目录
cd /opt/zx-card-py

# 拉取最新代码
git pull

# 重启服务
sudo systemctl restart zxcard-api

# 查看启动状态
sudo systemctl status zxcard-api
```

### 步骤 3：测试数据库连接

```bash
# 进入项目目录
cd /opt/zx-card-py

# 激活虚拟环境
source venv/bin/activate

# 测试数据库连接
python3 << 'PYEOF'
from api.db import get_db, engine
from api.models import Card

# 测试连接
try:
    print("Testing database connection...")
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("✓ Database connection OK")
    
    # 测试查询
    print("\nTesting Card query...")
    from sqlalchemy.orm import Session
    db = Session(engine)
    count = db.query(Card).count()
    print(f"✓ Found {count} cards in database")
    
    # 测试搜索
    print("\nTesting search query...")
    result = db.query(Card).filter(Card.color.in_(["白"])).limit(5).all()
    print(f"✓ Found {len(result)} white cards")
    for card in result:
        print(f"  - {card.cn_name} ({card.card_number})")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
PYEOF
```

### 步骤 4：检查配置文件

```bash
# 查看配置
cat /opt/zx-card-py/.env

# 确保以下配置正确：
# MYSQL_HOST=127.0.0.1
# MYSQL_PORT=3306
# MYSQL_USER=root
# MYSQL_PASSWORD=Zxcard@2024
# MYSQL_DB=zxcard
# USE_SQLITE=false
```

### 步骤 5：验证数据库表

```bash
# 登录 MySQL
sudo mysql -uroot -pZxcard@2024 zxcard

# 检查表结构
SHOW TABLES;
DESCRIBE cards;

# 检查数据
SELECT COUNT(*) FROM cards;
SELECT * FROM cards LIMIT 5;

# 检查白色卡牌
SELECT COUNT(*) FROM cards WHERE color = '白';
SELECT card_number, cn_name FROM cards WHERE color = '白' LIMIT 5;

# 退出
EXIT;
```

---

## 常见问题和解决方案

### 问题 1：数据库连接失败

**错误信息：**
```
Can't connect to MySQL server
Connection refused
```

**解决方案：**
```bash
# 检查 MySQL 服务状态
sudo systemctl status mysql

# 如果未运行，启动服务
sudo systemctl start mysql

# 重启 API 服务
sudo systemctl restart zxcard-api
```

### 问题 2：表不存在

**错误信息：**
```
Table 'zxcard.cards' doesn't exist
```

**解决方案：**
```bash
# 检查数据库
sudo mysql -uroot -pZxcard@2024 -e "USE zxcard; SHOW TABLES;"

# 如果表不存在，重新导入数据
cd /opt/zx-card-py
source venv/bin/activate

# 如果有 SQLite 数据库，重新导入
python export_to_mysql.py
```

### 问题 3：列名不匹配

**错误信息：**
```
Unknown column 'color' in 'field list'
```

**解决方案：**
```bash
# 检查表结构
sudo mysql -uroot -pZxcard@2024 zxcard -e "DESCRIBE cards;"

# 如果列名不对，重建表
# 备份数据
mysqldump -uroot -pZxcard@2024 zxcard > backup.sql

# 删除并重建
sudo mysql -uroot -pZxcard@2024 zxcard << 'SQL'
DROP TABLE IF EXISTS cards;
CREATE TABLE cards (
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
    INDEX idx_jp_name (jp_name),
    INDEX idx_color (color),
    INDEX idx_rarity (rarity),
    INDEX idx_type (type),
    INDEX idx_series (series)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
SQL

# 重新导入数据
cd /opt/zx-card-py
source venv/bin/activate
python export_to_mysql.py
```

### 问题 4：USE_SQLITE 配置错误

**错误信息：**
```
no such table: cards
```

**解决方案：**
```bash
# 确保 USE_SQLITE=false
sudo nano /opt/zx-card-py/.env

# 修改为：
# USE_SQLITE=false

# 保存并重启
sudo systemctl restart zxcard-api
```

### 问题 5：依赖包缺失

**错误信息：**
```
ModuleNotFoundError: No module named 'pymysql'
```

**解决方案：**
```bash
cd /opt/zx-card-py
source venv/bin/activate
pip install pymysql sqlalchemy
sudo systemctl restart zxcard-api
```

---

## 完整诊断脚本

创建并运行此诊断脚本：

```bash
# 创建诊断脚本
cat > /tmp/diagnose.sh << 'SCRIPT'
#!/bin/bash

echo "================================"
echo "ZX Card API 诊断脚本"
echo "================================"
echo ""

# 1. 检查服务状态
echo "1. 检查 API 服务状态..."
sudo systemctl status zxcard-api --no-pager | head -15

# 2. 检查 MySQL 服务
echo ""
echo "2. 检查 MySQL 服务状态..."
sudo systemctl status mysql --no-pager | head -10

# 3. 检查配置文件
echo ""
echo "3. 检查配置文件..."
if [ -f /opt/zx-card-py/.env ]; then
    echo "✓ .env 文件存在"
    grep -E "MYSQL_|USE_SQLITE" /opt/zx-card-py/.env | sed 's/PASSWORD=.*/PASSWORD=***/'
else
    echo "✗ .env 文件不存在"
fi

# 4. 检查数据库表
echo ""
echo "4. 检查数据库表..."
sudo mysql -uroot -pZxcard@2024 zxcard -e "SHOW TABLES;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ 数据库连接成功"
    sudo mysql -uroot -pZxcard@2024 zxcard -e "SELECT COUNT(*) as total FROM cards;" 2>/dev/null
else
    echo "✗ 数据库连接失败"
fi

# 5. 检查最近的错误日志
echo ""
echo "5. 最近的错误日志（最后20行）..."
sudo journalctl -u zxcard-api -n 20 --no-pager | grep -i error || echo "无明显错误"

echo ""
echo "================================"
echo "诊断完成"
echo "================================"
SCRIPT

# 运行诊断
bash /tmp/diagnose.sh
```

---

## 测试 API

修复后使用以下命令测试：

```bash
# 测试健康检查
curl http://118.195.191.67:8000/health

# 测试常量接口
curl http://118.195.191.67:8000/api/constants

# 测试搜索接口
curl -X POST http://118.195.191.67:8000/api/cards/search \
  -H "Content-Type: application/json" \
  -d '{"colors":["白"],"page_size":5}'

# 如果成功，应返回类似：
# {"items":[{...卡牌数据...}],"next_cursor":null}
```

---

## 远程协助

如果以上步骤无法解决问题，请提供以下信息：

1. **服务日志**（最近100行）：
   ```bash
   sudo journalctl -u zxcard-api -n 100 --no-pager > /tmp/api_logs.txt
   cat /tmp/api_logs.txt
   ```

2. **数据库状态**：
   ```bash
   sudo mysql -uroot -pZxcard@2024 zxcard -e "
   SELECT 
     TABLE_NAME, 
     TABLE_ROWS, 
     DATA_LENGTH, 
     INDEX_LENGTH 
   FROM information_schema.TABLES 
   WHERE TABLE_SCHEMA='zxcard';
   "
   ```

3. **配置文件**（隐藏密码）：
   ```bash
   cat /opt/zx-card-py/.env | sed 's/PASSWORD=.*/PASSWORD=***/'
   ```

---

## 预防措施

修复后，建议执行以下操作：

1. **添加监控**：
   ```bash
   # 创建监控脚本
   sudo nano /usr/local/bin/monitor_zxcard.sh
   
   # 添加内容：
   #!/bin/bash
   if ! systemctl is-active --quiet zxcard-api; then
       echo "API service is down, restarting..."
       sudo systemctl restart zxcard-api
   fi
   
   # 添加定时任务
   sudo crontab -e
   # 添加：*/5 * * * * /usr/local/bin/monitor_zxcard.sh
   ```

2. **启用日志轮转**：
   ```bash
   sudo nano /etc/logrotate.d/zxcard-api
   
   # 添加：
   /var/log/zxcard/*.log {
       daily
       rotate 7
       compress
       delaycompress
       notifempty
       create 0640 root root
   }
   ```

3. **定期备份数据库**：
   ```bash
   # 创建备份脚本
   sudo nano /usr/local/bin/backup_zxcard_db.sh
   
   # 添加：
   #!/bin/bash
   mysqldump -uroot -pZxcard@2024 zxcard > /backup/zxcard_$(date +%Y%m%d).sql
   find /backup -name "zxcard_*.sql" -mtime +7 -delete
   
   # 添加定时任务（每天凌晨2点）
   sudo crontab -e
   # 添加：0 2 * * * /usr/local/bin/backup_zxcard_db.sh
   ```

---

**如有问题，请查看日志并提供具体错误信息。**
