# AGENTS.md

> 参与本项目的 AI / Agent / 开发者，动手前先读完本文件。

## 一、项目定位

- **dsh-starrail-plugin**：dsh-roost 的《崩坏：星穹铁道》QQ 机器人插件，结合 DeepSeek 做账号点评
- 部署场景：公开群，10~200 人；最终开源（MIT）
- 核心原则：快速落地优先、复用成熟开源方案、米游社字段一律以官方文档为准、Cookie 严禁明文外泄

## 二、架构（关键，先读这段）

本项目是 **roost「外部插件」**，不是内建插件，也不是 HTTP 服务。

- 进程由 roost 用 `python main.py` 拉起，**stdin/stdout NDJSON 协议**（一行一个 JSON）
- `main.py` 是最薄的一层：收消息 → 调 `core.router.handle()` → `reply`
- **stdout 只能写协议 JSON**。任何日志、print、traceback 打进去都会破坏协议，导致插件失效。
  日志统一走 `core/utils/logger.py`（已强制 stderr）
- 官方协议文档：`C:\Users\admin\.dsh\dsh-roost\roost\docs\插件协议.md`
  （另有 `插件开发规范.md`）。协议细节以该文档为准，不要凭记忆写
- roost 已下发 `dataDir`，SQLite 必须放该目录（按机器人隔离），不要写死项目内路径

| 层 | 位置 | 职责 |
|---|---|---|
| 协议入口 | `main.py` | 注册命令、解析 msg、调路由、发 reply |
| 路由 | `core/router.py` | 与传输无关的命令分发，可脱离 roost 单测 |
| 米游社接口 | `core/api/` | DS 签名、请求封装、字段清洗 |
| 业务 | `core/bind/`、`core/character/`、`core/gacha/` | 绑定、练度、抽卡 |
| 基建 | `core/utils/` | 日志(脱敏)、SQLite、频率限制 |

**命令前缀**：roost 用可配置前缀（默认 `/`），星铁社区习惯 `#`。
因此 `main.py` 同时做两件事：注册 roost 命令（`/星铁体力`）+ 被动监听 `#星铁体力`。
新增命令两边都要挂，且都走 `core/router.handle()`，不要在入口里写业务逻辑。

## 三、运行与调试

**环境坑**：PATH 上的 `python` 可能是别的运行时，没装依赖。本机可用的是
`D:\Program Files\Python312\python.exe`。但**部署到 roost 后不需要管这个**——
放了 `requirements.txt` 后，roost 会自动建 `plugins/<id>/.venv` 并用它启动插件。

```powershell
# 协议冒烟测试（不需要连 QQ，模拟 roost 喂 stdin）
Set-Location -LiteralPath "D:\Personal data\星铁机器人"
& "D:\Program Files\Python312\python.exe" scripts\smoke_test.py
```

**验收标准**：冒烟测试必须输出 `结论: 通过`（ready 正常、stdout 非法行 0、各分支回复正确、闲聊不刷屏）。

**米游社接口自检**：用假 Cookie 打真实接口，返回业务错误码（-100 / 10001）说明签名与请求头正确；
返回签名类错误才是 DS 算法问题。当前统一用 `client_type=5` + 4X salt + DS2（该 salt 不随版本漂移）；
`client_type=2` 的 K2 salt 随版本变化，容易失效，不要用。

**接口规范来源**：`https://uigf.org/zh/mihoyo-api-collection/`

## 四、目录

```
main.py               # roost 插件入口（NDJSON 协议）
roost_sdk.py          # 官方 Python SDK，从 roost sdk/python 拷贝，勿改
plugin.json           # 插件元信息，id 必须与部署文件夹名一致
requirements.txt      # roost 自动装进插件专属 .venv
core/
├── router.py         # 命令路由（传输无关）
├── api/              # client.py(请求+签名) config.py ds_sign.py record.py
├── bind/             # service.py（Cookie 绑定/解绑）
├── character/        # 练度（待实现）
├── gacha/            # 抽卡（待实现）
├── render/           # 图片渲染（待实现）
├── ai/               # DeepSeek（待实现）
└── utils/            # logger(强制stderr+脱敏) store(SQLite) ratelimit
scripts/smoke_test.py # 协议冒烟测试
```

命名：Python snake_case；类 PascalCase；常量 UPPER_SNAKE_CASE。

## 五、Git

- `main` 保持可运行；功能从 `feature/<模块>-<描述>` 出分支
- commit 格式 `<类型>: <描述>`，类型：feat/fix/refactor/docs/chore/test/style

## 六、开发与红线

开发顺序：数据结构 → 数据层 → 业务层 → 接入路由。每个功能必须验证：
正常返回 / Cookie 失效 / 网络失败 / 未绑定 / 群聊私聊区分 / 频率限制。

红线：
- 禁止往 stdout 写任何非协议内容
- 禁止日志打印完整 Cookie / authkey
- 禁止群聊接收或回显 Cookie
- 禁止硬编码接口 URL（统一 `core/api/config.py`）与数据目录
- 禁止凭记忆写米游社字段，一律查 UIGF 文档
- 禁止改 `roost_sdk.py`（官方文件，升级会被覆盖）

## 七、进度

- **阶段0 环境搭建** ✅ roost 插件骨架、DS 签名（真实接口已验证）、路由、SQLite、日志、频率限制、协议冒烟测试
- **阶段1 账号绑定** ✅ Cookie 手动绑定（自动拉 UID/区服/昵称）、校验、解绑、群聊拦截 ｜ ⬜ 扫码登录、Cookie 巡检
- **阶段2 练度查询** ⬜ 首页信息、角色详情、伤害预期
- **阶段3 抽卡分析** ⬜ authkey 解析、全量拉取、统计保底、UIGF 导出
- **阶段4 图片渲染** ⬜ Playwright 引擎与三类卡片
- **阶段5 AI 能力** ⬜ 自然语言解析、练度点评、账号诊断

## 八、部署到 roost

插件目录名与 `plugin.json` 的 `id` 必须一致，roost 才会识别。
把整个项目目录（含 `core/`、`main.py`、`plugin.json`、`requirements.txt`）拷到
`C:\Users\admin\.dsh\dsh-roost\roost\plugins\dsh-starrail\`，
首次加载会自动建 `.venv` 装依赖，之后热重载（默认 2 秒）。

**最后更新**：2026-11-07
