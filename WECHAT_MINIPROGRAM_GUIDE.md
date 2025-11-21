# 微信小程序 API 对接指南

## 概述

本指南帮助您将部署好的 ZX Card API 服务与微信小程序对接。

**您的小程序信息：**
- AppID: `wx4387eb448d6892c5`
- 项目名称: zx-catmarket

---

## 一、前置条件

### 1.1 已完成的工作
- ✅ 服务器已部署（运行 `deploy_all_in_one.sh`）
- ✅ API 服务已启动（端口 8000）
- ✅ 数据库已导入（10,413 条卡牌数据）

### 1.2 需要准备
- 一个已备案的域名
- 服务器公网 IP 地址
- 微信公众平台管理员权限

---

## 二、配置域名和 HTTPS

### 2.1 域名解析

1. 登录您的域名注册商管理后台
2. 添加 A 记录：
   ```
   主机记录: api (或其他子域名)
   记录类型: A
   记录值: 您的服务器公网 IP
   TTL: 600
   ```
3. 等待 DNS 生效（通常 5-10 分钟）

### 2.2 安装 Nginx

```bash
# SSH 登录服务器
sudo apt install nginx -y
```

### 2.3 配置 SSL 证书（使用 Let's Encrypt 免费证书）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 申请证书（将 api.yourdomain.com 替换为您的域名）
sudo certbot --nginx -d api.yourdomain.com

# 按提示输入邮箱并同意服务条款
```

### 2.4 配置 Nginx 反向代理

创建配置文件：
```bash
sudo nano /etc/nginx/sites-available/zxcard-api
```

粘贴以下配置（替换域名）：
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS 配置（如需要）
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods 'GET, POST, OPTIONS';
        add_header Access-Control-Allow-Headers 'DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type';
    }
}
```

启用配置：
```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/zxcard-api /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 2.5 测试 HTTPS

```bash
# 测试 HTTPS 访问
curl https://api.yourdomain.com/health

# 应返回：{"ok":true}
```

---

## 三、微信公众平台配置

### 3.1 登录微信公众平台

访问：https://mp.weixin.qq.com

使用小程序管理员账号登录

### 3.2 获取 AppSecret

1. 进入：开发管理 → 开发设置
2. 找到"开发者ID"部分
3. 点击 AppSecret 后的"重置"按钮
4. **立即复制并保存** AppSecret（只显示一次）

### 3.3 配置服务器域名

1. 在"开发设置"页面，找到"服务器域名"
2. 点击"修改"
3. 配置以下域名：

**request合法域名：**
```
https://api.yourdomain.com
```

**注意事项：**
- 必须使用 HTTPS
- 不能使用 IP 地址
- 域名必须已备案
- 每月只能修改 5 次

### 3.4 更新服务器配置

SSH 登录服务器，更新 AppSecret：

```bash
# 编辑配置文件
sudo nano /opt/zx-card-py/.env

# 修改以下行（替换为实际的 AppSecret）
WECHAT_APPID=wx4387eb448d6892c5
WECHAT_SECRET=your_actual_app_secret_here

# 保存后重启服务
sudo systemctl restart zxcard-api
```

---

## 四、API 接口说明

### 4.1 基础信息

- **Base URL**: `https://api.yourdomain.com`
- **Content-Type**: `application/json`
- **编码**: UTF-8

### 4.2 主要接口

#### 1. 健康检查
```
GET /health
```
响应：
```json
{
  "ok": true
}
```

#### 2. 获取常量数据
```
GET /api/constants
```
响应：
```json
{
  "color": ["无", "红", "蓝", "白", "黑", "绿"],
  "rarity": [["R", "R"], ["SR", "SR"], ...],
  "type": ["玩家", "Z/X", ...],
  "mark": [["", "无"], ["ES", "觉醒之种"], ...],
  "tags": ["生命恢复", "起始卡", ...]
}
```

#### 3. 搜索卡牌
```
POST /api/cards/search
Content-Type: application/json
```
请求体：
```json
{
  "keyword": "搜索关键词",
  "colors": ["红", "蓝"],
  "rarities": ["SR", "UR"],
  "types": ["Z/X"],
  "marks": ["ES"],
  "tags": ["起始卡"],
  "series": ["B01"],
  "cost": {"min": 1, "max": 5},
  "power": {"min": 1000, "max": 5000},
  "page_size": 20
}
```

响应：
```json
{
  "items": [
    {
      "id": 1,
      "color": "红",
      "card_number": "B01-001",
      "series": "B01",
      "rarity": "R",
      "type": "Z/X",
      "jp_name": "カード名",
      "cn_name": "卡牌名",
      "cost": "3",
      "power": "2000",
      "race": "种族",
      "note": "备注",
      "text_full": "效果文本",
      "image_url": "https://...",
      "detail_url": "https://..."
    }
  ],
  "next_cursor": "下一页游标或null"
}
```

#### 4. 获取卡牌详情
```
GET /api/cards/{card_id}
```

---

## 五、小程序端代码示例

### 5.1 配置 API 地址

在小程序项目中创建配置文件：

**config/api.js**
```javascript
const API_BASE_URL = 'https://api.yourdomain.com';

module.exports = {
  API_BASE_URL,
  // API 端点
  API: {
    HEALTH: `${API_BASE_URL}/health`,
    CONSTANTS: `${API_BASE_URL}/api/constants`,
    SEARCH_CARDS: `${API_BASE_URL}/api/cards/search`,
    CARD_DETAIL: `${API_BASE_URL}/api/cards`,
  }
};
```

### 5.2 封装请求方法

**utils/request.js**
```javascript
const { API_BASE_URL } = require('../config/api');

/**
 * 封装 wx.request
 */
function request(options) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...options.header
      },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail: (error) => {
        reject(error);
      }
    });
  });
}

module.exports = {
  request,
  
  // GET 请求
  get(url, data) {
    return request({
      url,
      method: 'GET',
      data
    });
  },
  
  // POST 请求
  post(url, data) {
    return request({
      url,
      method: 'POST',
      data
    });
  }
};
```

### 5.3 调用示例

**pages/search/search.js**
```javascript
const { API } = require('../../config/api');
const { get, post } = require('../../utils/request');

Page({
  data: {
    cards: [],
    loading: false
  },

  onLoad() {
    this.loadConstants();
  },

  // 加载常量数据
  async loadConstants() {
    try {
      const constants = await get(API.CONSTANTS);
      this.setData({
        constants
      });
    } catch (error) {
      console.error('加载常量失败:', error);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  // 搜索卡牌
  async searchCards() {
    this.setData({ loading: true });
    
    try {
      const result = await post(API.SEARCH_CARDS, {
        keyword: this.data.keyword,
        colors: this.data.selectedColors,
        page_size: 20
      });
      
      this.setData({
        cards: result.items,
        loading: false
      });
    } catch (error) {
      console.error('搜索失败:', error);
      this.setData({ loading: false });
      wx.showToast({
        title: '搜索失败',
        icon: 'none'
      });
    }
  },

  // 查看卡牌详情
  async viewCardDetail(e) {
    const cardId = e.currentTarget.dataset.id;
    
    try {
      const card = await get(`${API.CARD_DETAIL}/${cardId}`);
      
      // 跳转到详情页
      wx.navigateTo({
        url: `/pages/detail/detail?card=${JSON.stringify(card)}`
      });
    } catch (error) {
      console.error('获取详情失败:', error);
      wx.showToast({
        title: '获取详情失败',
        icon: 'none'
      });
    }
  }
});
```

---

## 六、测试验证

### 6.1 测试流程

1. **本地测试**
   ```bash
   # 测试 HTTPS
   curl https://api.yourdomain.com/health
   
   # 测试搜索
   curl -X POST https://api.yourdomain.com/api/cards/search \
     -H "Content-Type: application/json" \
     -d '{"keyword":"红","page_size":5}'
   ```

2. **小程序开发工具测试**
   - 打开小程序开发工具
   - 确保"不校验合法域名"已关闭
   - 运行小程序并测试 API 调用

3. **真机测试**
   - 使用"预览"功能在手机上测试
   - 验证所有 API 调用正常

### 6.2 常见问题

#### 问题 1：request合法域名校验出错

**原因：** 域名未在微信公众平台配置

**解决：**
1. 确认域名已在"服务器域名"中配置
2. 域名必须使用 HTTPS
3. 等待配置生效（约 5 分钟）

#### 问题 2：SSL 证书错误

**解决：**
```bash
# 检查证书状态
sudo certbot certificates

# 续期证书
sudo certbot renew
```

#### 问题 3：API 返回 502

**解决：**
```bash
# 检查 API 服务状态
sudo systemctl status zxcard-api

# 查看日志
sudo journalctl -u zxcard-api -n 50

# 重启服务
sudo systemctl restart zxcard-api
```

---

## 七、生产环境建议

### 7.1 安全加固

1. **配置防火墙**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw deny 8000/tcp  # 不直接暴露 API 端口
   sudo ufw enable
   ```

2. **修改默认密码**
   ```bash
   # MySQL 密码
   sudo mysql -uroot -p
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_secure_password';
   
   # 更新 .env
   sudo nano /opt/zx-card-py/.env
   ```

3. **启用日志轮转**
   ```bash
   sudo nano /etc/logrotate.d/zxcard-api
   ```

### 7.2 监控告警

1. **设置 SSL 证书自动续期**
   ```bash
   # Certbot 会自动配置 cron 任务
   sudo certbot renew --dry-run
   ```

2. **监控服务状态**
   ```bash
   # 创建监控脚本
   sudo nano /usr/local/bin/check_zxcard.sh
   ```

### 7.3 备份策略

```bash
# 备份数据库
mysqldump -uroot -p zxcard > backup_$(date +%Y%m%d).sql

# 备份配置
tar -czf config_backup.tar.gz /opt/zx-card-py/.env
```

---

## 八、API 文档

完整的 API 文档可通过以下地址访问：

```
https://api.yourdomain.com/docs
```

这是一个自动生成的交互式 API 文档（Swagger UI），您可以：
- 查看所有接口详情
- 在线测试 API
- 查看请求/响应示例

---

## 九、联系支持

如遇到问题：

1. 查看服务器日志：
   ```bash
   sudo journalctl -u zxcard-api -f
   ```

2. 查看 Nginx 日志：
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. 参考文档：
   - [腾讯云文档](https://cloud.tencent.com/document)
   - [微信小程序文档](https://developers.weixin.qq.com/miniprogram/dev/framework/)
   - [项目 GitHub](https://github.com/kll85757/zx-card-py)

---

**祝您对接顺利！** 🎉
