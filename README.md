# 多源数据采集与RPA自动化平台

面向网页抓取、API接入、增量采集、RPA流程编排、数据校验与采集监控的数据工程平台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 数据源配置 | `datasource` | 数据源 | 源端编号、连接类型、接入地址 |
| 网页采集规则 | `crawler` | 采集规则 | 规则编号、目标网址、页面选择器 |
| API接入管理 | `apiclient` | API客户端 | 客户端编号、接口名称、请求方法 |
| 增量采集 | `incremental` | 增量游标 | 游标编号、来源标识、增量字段 |
| RPA任务编排 | `robot_task` | RPA任务 | 任务编号、任务名称、页面定位器 |
| 数据接入通道 | `ingestion` | 接入通道 | 通道编号、通道名称、输入格式 |
| 格式解析器 | `parser` | 解析配置 | 解析编号、输入格式、输出格式 |
| 字段别名映射 | `field_alias` | 别名映射 | 映射编号、标准字段、来源名称、采样站、有效批次、核对证据 |
| 采集结果校验 | `validator` | 校验规则 | 规则编号、校验字段、校验类型 |
| 采集去重 | `dedup` | 去重策略 | 策略编号、输入来源、去重键 |
| 采集调度 | `schedule` | 调度计划 | 计划编号、关联任务、调度周期 |
| 采集监控 | `monitor` | 监控面板 | 面板编号、采集源总数、今日采集量 |
| 采集日志 | `log_viewer` | 日志条目 | 日志编号、关联任务、日志级别 |
| 凭证管理 | `auth` | 认证凭证 | 凭证编号、凭证类型、关联数据源 |
| 采集转换管道 | `transform` | 转换节点 | 节点编号、输入来源、输出目标 |
| 数据流转编排 | `flow` | 流转管道 | 管道编号、管道名称、起始节点 |
| 数据血缘追踪 | `lineage` | 血缘关系 | 关系编号、上游节点、下游节点 |
| 采集报告 | `report` | 采集报告 | 报告编号、采集源、统计周期 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

## 字段别名映射与解析校验联动

格式解析器与采集结果校验不再各自登记字段名，两处字段识别收拢为
`app/services/field_mapping.py` 的共用映射解析，数据落在采集字段别名映射
数据集（`field_alias`）里：

- 映射按（采样站， 有效批次）限定作用域：一个站点的「流量」不一定就是另一站
  的「流量」，同名来源不按文本相等折叠；旧批次映射原样保留、可按批次查询。
- `POST /api/field_alias/ingest` 读取传感器表头与来源字段名归并进数据集，
  新来源登记为待核对，不覆盖旧映射；`GET /api/field_alias/resolve` 查看某站点
  某批次的有效映射。
- `POST /api/parser/parse` 按映射把传感器原值写成标准字段（`parse_result`），
  记录每个标准字段实际使用的原字段名与核对证据；候选来源读数不一致的行
  标记为待核对。原始样本经 `GET /api/parser/samples` 始终可查。
- `POST /api/validator/validate` 读取同一份解析结果判定阈值（如超温规则
  VALI-9010，阈值 20℃），超阈值开立处置单（`disposal`）；
  `GET /api/validator/detail` 逐行给出标准字段值、实际使用的原字段名、
  候选来源冲突与处置单，尚欠核对的原始行单独列出。

示例：河口站 BATCH-2026-1101 批表头同时有「水温」与「河水温度」，两列都有
校准记录；已确认来源为「河水温度」。第 10 行「水温」读 19℃、「河水温度」读
24℃，分处超温阈值 20℃ 两侧——处置单 DISP 单按已确认来源开立，其有无及
依据（来源字段、读数、阈值、冲突证据）都能从第 10 行还原。
