#!/usr/bin/env python3
"""
将 SQLite 数据库导出到 MySQL
用于腾讯云部署前的数据迁移
"""
import sqlite3
import pymysql
from pymysql.cursors import DictCursor
import sys
from typing import Optional

# 配置
SQLITE_PATH = "zxcard.db"

# MySQL 配置（腾讯云）- 需要根据实际情况修改
MYSQL_CONFIG = {
    "host": "your-tencentdb-host.mysql.tencentcdb.com",  # 腾讯云 MySQL 地址
    "port": 3306,
    "user": "root",
    "password": "your_password",  # 替换为实际密码
    "database": "zxcard",
    "charset": "utf8mb4",
}


def create_mysql_schema(cursor):
    """创建 MySQL 数据库表结构"""
    print("创建数据库表结构...")
    
    # 创建 cards 表
    cursor.execute("""
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
            INDEX idx_jp_name (jp_name),
            INDEX idx_series (series),
            INDEX idx_rarity (rarity),
            INDEX idx_type (type),
            INDEX idx_color (color)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    print("表结构创建完成")


def export_data(sqlite_path: str, mysql_config: dict, batch_size: int = 500):
    """导出 SQLite 数据到 MySQL"""
    
    # 连接 SQLite
    print(f"连接 SQLite 数据库: {sqlite_path}")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # 连接 MySQL
    print(f"连接 MySQL 数据库: {mysql_config['host']}")
    try:
        mysql_conn = pymysql.connect(**mysql_config)
        mysql_cursor = mysql_conn.cursor()
        
        # 创建表结构
        create_mysql_schema(mysql_cursor)
        mysql_conn.commit()
        
        # 清空现有数据（可选）
        print("清空现有数据...")
        mysql_cursor.execute("TRUNCATE TABLE cards")
        mysql_conn.commit()
        
        # 读取所有数据
        print("读取 SQLite 数据...")
        sqlite_cursor.execute("SELECT * FROM cards")
        rows = sqlite_cursor.fetchall()
        total = len(rows)
        print(f"共 {total} 条数据")
        
        # 批量插入 MySQL
        print("开始导入 MySQL...")
        sql = """
            INSERT INTO cards (
                color, card_number, series, rarity, type,
                jp_name, cn_name, cost, power, race,
                note, text_full, image_url, detail_url
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """
        
        inserted = 0
        for i in range(0, total, batch_size):
            batch = rows[i:i + batch_size]
            values = [
                (
                    row['color'], row['card_number'], row['series'],
                    row['rarity'], row['type'], row['jp_name'],
                    row['cn_name'], row['cost'], row['power'],
                    row['race'], row['note'], row['text_full'],
                    row['image_url'], row['detail_url']
                )
                for row in batch
            ]
            
            mysql_cursor.executemany(sql, values)
            mysql_conn.commit()
            inserted += len(batch)
            print(f"已导入 {inserted}/{total} 条 ({inserted*100//total}%)")
        
        # 验证数据
        mysql_cursor.execute("SELECT COUNT(*) as count FROM cards")
        count = mysql_cursor.fetchone()[0]
        print(f"\n✓ 导入完成！MySQL 中共有 {count} 条记录")
        
        if count != total:
            print(f"⚠️  警告：数据数量不匹配！SQLite: {total}, MySQL: {count}")
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        sys.exit(1)
    finally:
        mysql_cursor.close()
        mysql_conn.close()
        sqlite_cursor.close()
        sqlite_conn.close()


def test_connection(mysql_config: dict) -> bool:
    """测试 MySQL 连接"""
    print("测试 MySQL 连接...")
    try:
        conn = pymysql.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"✓ 连接成功！MySQL 版本: {version}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("SQLite 到 MySQL 数据迁移工具")
    print("=" * 60)
    print()
    
    # 检查参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            test_connection(MYSQL_CONFIG)
            sys.exit(0)
        elif sys.argv[1] == "--help":
            print("使用方法:")
            print("  python export_to_mysql.py           # 执行数据迁移")
            print("  python export_to_mysql.py --test    # 测试 MySQL 连接")
            print("  python export_to_mysql.py --help    # 显示帮助")
            print()
            print("注意: 请先在脚本中配置 MYSQL_CONFIG")
            sys.exit(0)
    
    # 确认执行
    print("⚠️  警告: 此操作将清空 MySQL 中的现有数据！")
    print(f"SQLite 源: {SQLITE_PATH}")
    print(f"MySQL 目标: {MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}")
    print()
    confirm = input("确认继续？(yes/no): ")
    
    if confirm.lower() != "yes":
        print("已取消")
        sys.exit(0)
    
    # 执行迁移
    export_data(SQLITE_PATH, MYSQL_CONFIG)
    print()
    print("=" * 60)
    print("迁移完成！")
    print("=" * 60)
