## 前端需求说明 + API 手册（小程序联调）

### 基本信息
- 基础地址（本地开发）: `http://127.0.0.1:8000`
- 认证: 无（MVP）
- CORS: 已全放开
- 数据源: 本地 SQLite（可切换 MySQL/Meilisearch/Redis，不影响前端接口）
- 约定:
  - 所有接口返回 JSON
  - 错误统一 `{ "detail": "错误信息" }`

### 资源模型
- Card
  - id: number
  - color: string
  - card_number: string（如 `B01-001`）
  - series: string（如 `B01`/`E01`）
  - rarity: string
  - type: string
  - jp_name: string
  - cn_name: string
  - cost: string（可能为空字符串）
  - power: string（可能为空字符串）
  - race: string
  - note: string
  - text_full: string
  - image_url: string
  - detail_url: string

- Constants（筛选项元数据）
  - color: string[]
  - rarity: [string, string][]
  - type: string[]
  - mark: [string, string][]（预留）
  - tags: string[]（预留）
  - series: any（预留）

---

### 接口列表

#### 健康检查
- GET `/health`
- 响应: `{ "ok": true }`

#### 常量（前端筛选项初始化）
- GET `/api/constants`
- 响应示例：
{
  "color": ["无","红","蓝","白","黑","绿"],
  "rarity": [["R","R"],["SR","SR"],["UR","UR"],["WR","WR"],["BR","BR"],["OBR","OBR"]],
  "type": ["玩家","玩家EX","Z/X","Z/X EX","Z/X OB","Z/X TOKEN","事件","事件EX","升格","升格EX","剑临","标记","链结"],
  "mark": [["","无"],["ES","觉醒之种"],["IG","点燃"]],
  "tags": ["生命恢复","起始卡","门扉卡","超限驱动"],
  "series": {}
}

#### 卡片详情
- GET `/api/cards/{id}`
- 成功返回 Card；不存在返回 `404 { "detail": "Not found" }`

#### 卡片搜索（MVP：数据库 LIKE 过滤）
- POST `/api/cards/search`
- 请求体：
{
  "keyword": "可选，关键词",
  "colors": ["红","蓝"],
  "rarities": ["SR","UR"],
  "types": ["Z/X","事件"],
  "series": ["B01","E01"],
  "cursor": null,
  "page_size": 50
}
- 响应体：
{
  "items": [],
  "next_cursor": null
}
- 说明：
  - `keyword` 在 `cn_name | jp_name | card_number` 做模糊匹配（`%keyword%`）
  - `colors/rarities/types/series` 为 IN 过滤，与 `keyword` 叠加为 AND
  - `page_size`：1~200，默认 50；`next_cursor` 目前固定 `null`

---

### 前端交互建议
- 启动后先调用 `/api/constants` 填充筛选项
- 搜索与筛选为 AND 关系，`keyword` 建议 300ms 防抖
- 列表项展示建议：
  - 标题：`cn_name`（fallback `jp_name`）
  - 副标题：`card_number · rarity · type`
  - 标签：`color`、`series`
  - 图片：`image_url`（懒加载）
- 空值展示：`cost/power` 为空字符串时显示 “—”
- 错误处理：
  - 404：提示“卡片不存在或已下架”
  - 500：提示“服务繁忙，请稍后重试”

---

### 示例（可直接用于 Postman/网络层）

GET 常量
GET http://127.0.0.1:8000/api/constants

GET 详情
GET http://127.0.0.1:8000/api/cards/1

POST 搜索（关键词）
POST http://127.0.0.1:8000/api/cards/search
Content-Type: application/json

{ "keyword": "ZX", "page_size": 20 }

POST 搜索（多条件）
{
  "keyword": "天使",
  "colors": ["红","蓝"],
  "rarities": ["SR","UR"],
  "types": ["Z/X","事件"],
  "series": ["B01","E01"],
  "page_size": 50
}

---

### 未来扩展（对前端改动最小）
- 接入 Meilisearch 后：增强搜索质量、分页（可能新增 `sort`、`next_cursor`），路径与入参基本不变
- 分页：将来提供基于 `next_cursor` 的“加载更多”
- `marks/tags`：后续纳入过滤，`/api/constants` 补充枚举即可


