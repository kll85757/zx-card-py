## THE一灭寂（zxcard.yimieji.com）搜索页业务说明与采集数据对齐（PRD）

### 1. 概览
- 目标站点：`https://zxcard.yimieji.com/search`（Nuxt/SSR + 客户端渲染，Ant Design UI）
- 当前我们已抓取的源：补充包页（`/package` → `/Package/{pack}`），滚动加载全部卡牌并解析列表项详情；同时保留了列表页与详情页的离线 HTML（用于二次解析和兜底）。
- 我们导出的字段（`zx2_cards_full.csv`）：
  - color, card_number, series, rarity, type, jp_name, cn_name, cost, power, race, note, text_full, image_url, detail_url。
- 搜索页是“聚合入口”，承载字段枚举、系列/补充包结构、标签等常量，前端根据条件组合调用后端接口拉取卡列表，再以无限滚动/分页渲染。

### 2. 前端架构与页面形态
- 框架：Nuxt（SSR 首屏 + 客户端 Hydration）。
- UI：Ant Design（`ant-layout`/`ant-card`/`ant-list` 等）。
- 数据来源：
  - HTML 中包含 `window.__NUXT__`，嵌入了常量字典与“系列/补充包”完整枚举（见第 3 节）。
  - 卡牌检索结果并未直接嵌入 HTML，而是由前端 JS（引自 `engine-assets.moecard.cn/zxcard/*.js`）在运行时发起 API 请求加载。
- URL 形态：`/search#<随机指纹>`。Hash 用于前端状态去抖/避爬与浏览器回退；直接改 query 对分页不稳定。因此稳定抓取需模拟点击/滚动，或走包页面一次性加载。
- 列表加载：采用滚动增量加载，直到元素数量稳定（我们在脚本里以“多轮稳定阈值”判断加载完成）。

### 3. 业务常量与分类体系（来源：__NUXT__ state）
- 颜色（color）：[无/红/蓝/白/黑/绿/…]。
- 稀有度（rarity）：多层映射，既有标准 R/SR/UR/WR/BR/OBR/…，也包含线上抽卡扩展如 `SR-gacha` 等。
- 类型（type）：[玩家/玩家EX/Z/X/Z/X EX/Z/X OB/Z/X TOKEN/事件/事件EX/升格/升格EX/剑临/标记/链结]。
- 标记（mark）：[无, ES, IG]。
- 标签（tags）：如“生命恢复/起始卡/门扉卡/超限驱动/…”。
- 系列（series）与补充包（pack）：
  - 大类：补充包（Bxx）、额外补充包（Exx）、预构（Cxx/SDxx/…）、线上抽卡（Gxx）、PR/其他/IG 系列等。
  - 每个 pack 提供：`pack_prefix（如 B34）/pack_name/发行日/备注/封面` 等，并在备注中嵌入罕贵分布与封装规则。
- 这些常量在搜索页用于构造筛选项（颜色/稀有度/类型/标签/系列/补充包等）。

### 4. 搜索业务流程（推断+对照）
1) 页面初始化：
   - SSR 输出骨架 + 常量字典（见 3）。
   - 客户端加载 `engine-assets.moecard.cn/zxcard/*.js`，完成路由/状态初始化。
2) 条件构建：
   - 条件项来自常量：颜色/稀有度/类型/标签/系列/对应补充包。
   - 关键字：输入框（支持 CN/JP 名称、编号等）。
   - 其他数值条件：费用（cost）、力量（power），以及与玩法相关的“标记/机制标签”。
3) 触发查询：
   - 用户点击“搜索/修改”，前端将条件序列化，调用后端 API（POST/GET，URL 由打包 JS 决定），返回卡列表（分页/游标）。
   - URL hash 更新为随机值（避免前进/后退触发重复命中缓存/或作为去爬策略的一部分）。
4) 渲染与分页：
   - Ant List 渲染卡牌简表项：卡图、编号、CN/JP 名称、稀有度、类型、若可从列表解析也会显示费用/力量/种族。
   - 滚动加载：监听滚动，继续以同条件请求下一页（或下一游标），合并至列表。
5) 详情跳转：
   - 列表项链接至 `/Cards/{prefix}/{number}/{rarity?}`，详情包含完整文本、插画信息等。

和我们采集结果对齐：
- 列表面可直接解析到：`card_number/cn_name/jp_name/rarity/type/cost/power/race/image_url/detail_url`；
- 详情页（或包页扩展字段）可补齐：`text_full/note/series/color` 等；
- 我们通过“包页滚动加载”将同一 pack 下全部卡一次性注入列表 DOM，减少对分页 API 的依赖，使采集稳定。

### 5. 数据模型（对齐 CSV 与站点语义）
- 主键建议：`detail_url`（首选），退化到 `image_url`；对无 URL 场景用复合键：`card_number|rarity|cn_name|jp_name`。
- 字段映射：
  - color：映射 constants.color 的中文（如“红/蓝/白/…”）。
  - series：从 pack 前缀（Bxx/Eyy/…）与 __NUXT__ 中 series/pack 树关联，写入 `series=pack_prefix`，可另建维表保存 `series_name/pack_name`。
  - rarity/type/mark/tags：与 constants 取值对齐（中文显示名）。
  - cost/power/race：从列表或详情解析的数值/文本。
  - text_full/note：效果全文与备注（详情优先）。
  - image_url/detail_url：分别用于图像与详情访问。

### 6. 反爬与稳定性要点（与实现对应）
- Hash 随机化 + 前端状态：分页 URL 不可靠，必须“点击/滚动”驱动前端状态改变。
- GCM/网络报错：浏览器需关闭 Push/通知/后台网络；实现了失败重试与 driver 重建。
- 代理/证书问题：优先 Selenium Manager，失败再降级 webdriver-manager；清理系统代理。
- 内容稳定检测：通过“列表元素计数”多轮稳定阈值确认加载完成。
- 断点续跑：包序列可从指定 pack 恢复；0 结果的包记录并支持深滚重试。

### 7. 搜索 PRD（面向数据/功能联调）
1) 目标
   - 用户可在“高级搜索”按条件快速定位卡牌，支持跨系列/多条件组合，列表滚动加载，点击进入详情。

2) 角色
   - 玩家/收藏者：按名称、编号、系列、稀有度、颜色、费用、力量、机制标签等检索。
   - 维护者（后台）：维护常量字典（颜色/稀有度/类型/标签）、系列与补充包树以及卡牌库。

3) 数据源与字典
   - 常量字典：颜色/稀有度/类型/标记/标签（来自 __NUXT__ 或后端 constants API）。
   - 系列树：series → pack（包含 pack_prefix/名称/发行信息）。
   - 卡牌库：基础字段 + 文本 + 关联 pack/series。

4) 核心功能
   - 条件选择：
     - 关键字（支持 CN/JP 名称、编号模糊）。
     - 颜色/稀有度/类型/标记/标签 复选。
     - 系列/补充包：选择 series 时可全选子包，或精确到单个 pack。
     - 数值：费用区间/力量区间。
   - 结果列表：
     - 卡图缩略图、编号、CN/JP 名、稀有度、类型、颜色、费用、力量、种族。
     - 支持按编号/稀有度/时间排序。
     - 无限滚动加载；loading/空态显示。
   - 详情页：
     - 文本（text_full）、备注（note）、插画（illustrator，如后端提供）、所属系列/包、标签、标记。
   - 交互：
     - URL hash 记录本次查询指纹与条件快照（用于后退/分享）。

5) 接口（对外 PRD，基于当前前端形态的合理约定）
   - GET `/api/constants`：返回颜色/稀有度/类型/标记/标签/series→pack 树（与 __NUXT__ 一致）。
   - POST `/api/cards/search`：
     - body：{ keyword, colors[], rarities[], types[], marks[], tags[], series[], packs[], cost:{min,max}, power:{min,max}, sort, cursor, page_size }
     - resp：{ items:[{id,card_number,cn_name,jp_name,rarity,type,color,cost,power,race,image_url,detail_url,series,pack}], next_cursor }
   - GET `/api/cards/:id`：返回详情（含 text_full/note/illustrator/…）。

6) 非功能性要求
   - 性能：首屏 < 2s（SSR），翻页接口 P95 < 800ms；滚动追加无明显抖动。
   - 可用性：接口失败重试，给出用户提示；支持弱网。
   - 反爬：合理的速率限制与指纹；hash 随机值/游标不可预测。
   - 可观测性：前端埋点（条件/结果数/分页），后端日志（条件分布/耗时/错误）。

7) 和我们采集/导出对齐策略
   - 字段落库：一行即一张卡的“标准形态”；多变体（不同稀有度/不同插画版本）保留为多行，主键优先 `detail_url`。
   - 去重策略：
     - 保守：`detail_url` 唯一（不合并不同版本）。
     - 业务合并视图：按 `card_number` 聚合显示不同版本（需要二级分组）。
   - 数据质量：
     - 枚举映射到 `constants` 的标准值（稀有度大小写与命名同步）。
     - 数值字段（cost/power）标准化为整数/短横线转空。
     - 文本去噪：全/半角、空白、HTML 实体统一。

8) 边界与例外
   - 某些包页为空（站点未上卡或权限限制）：记录并稍后重试。
   - 列表可见字段不足：从详情页补齐；若仍缺失，保留空值并在“数据质量报表”标记。
   - 线上抽卡（Gxx）与 PR/其他：编号/稀有度体系与常规 B 系列差异较大，搜索需按 constants 完整支持。

### 8. 后续建议
- 增加“编号规范器”（如 E53-001、E53-001S、SEC 派生），便于聚合与排序。
- 建立维表：`packs(pack_prefix, pack_name, release_date, series_id, remark)` 与 `rarity_map(raw, normalized, order)`。
- 搜索服务化：在本地构建轻量索引（例如 SQLite/Full-Text 或 Whoosh/Meilisearch），用于离线分析与即时搜索。

### 9. 附录
- 采集产物：
  - `zx2_cards_full.csv`：完整字段导出。
  - `zx2_cards_full_deduped.csv`：按保守/或指定策略去重后的数据集。
  - `debug_yimieji/`：离线 HTML（包页、详情）用于复盘与二次解析。

### 10. API 设计文档

#### 接口概览
- **基础路径**: `http://localhost:8000`
- **认证方式**: 微信小程序签名验证（占位，当前无认证）
- **数据格式**: JSON
- **编码**: UTF-8

#### 接口列表

##### 1. 健康检查
- **路径**: `GET /health`
- **功能**: 检查服务是否正常运行
- **响应**: `{"ok": true}`

##### 2. 获取常量字典
- **路径**: `GET /api/constants`
- **功能**: 返回搜索页所需的常量枚举（颜色、稀有度、类型、标记、标签、系列树）
- **响应**:
```json
{
  "color": ["无", "红", "蓝", "白", "黑", "绿"],
  "rarity": [["R", "R"], ["SR", "SR"], ["UR", "UR"]],
  "type": ["玩家", "玩家EX", "Z/X", "Z/X EX"],
  "mark": [["", "无"], ["ES", "觉醒之种"]],
  "tags": ["生命恢复", "起始卡", "门扉卡"],
  "series": {}
}
```

##### 3. 搜索卡牌
- **路径**: `POST /api/cards/search`
- **功能**: 根据条件搜索卡牌，支持关键词、多维度过滤、分页
- **请求体**:
```json
{
  "keyword": "搜索关键词",
  "colors": ["红", "蓝"],
  "rarities": ["SR", "UR"],
  "types": ["Z/X", "Z/X EX"],
  "marks": ["ES"],
  "tags": ["起始卡"],
  "series": ["B01", "B02"],
  "packs": ["B01-001"],
  "cost": {"min": 1, "max": 5},
  "power": {"min": 1000, "max": 5000},
  "sort": "card_number",
  "cursor": "下一页游标",
  "page_size": 50
}
```
- **响应**:
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

##### 4. 获取卡牌详情
- **路径**: `GET /api/cards/{card_id}`
- **功能**: 根据ID获取单张卡牌的完整信息
- **路径参数**: `card_id` (整数)
- **响应**: 同搜索接口中的单个卡牌对象

#### 本地运行（MVP）
- 准备 MySQL/Redis/Meilisearch：
  - MySQL 建库 `zxcard`，更新 `.env`（参考 `api/config.py` 默认值）。
  - 启动 Meilisearch（本机 7700，masterKey）。
  - 启动 Redis（本机 6379）。
- 初始化并导入：
  - `python -m api.cli initdb`
  - `python -m api.cli import --csv zx2_cards_full.csv`
  - `python -m api.cli reindex`（后台 Celery 执行）
- 启动 API：
  - `uvicorn api.main:app --reload --port 8000`

#### 管理命令
- `python -m api.cli initdb` - 初始化数据库表结构
- `python -m api.cli import --csv <文件路径>` - 导入CSV数据到数据库
- `python -m api.cli reindex` - 重新构建搜索索引


