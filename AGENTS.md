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

### 已踩过的坑（真机部署时逐个撞过，别再犯）

1. **`requirements.txt` 必须纯 ASCII**。写中文注释会让 pip 在 GBK 环境下 `UnicodeDecodeError`，
   表现为「安装 Python 依赖失败」。roost 用系统编码解码依赖文件，不认 UTF-8 中文。
2. **不要用 SDK 的 `alias=` 注册别名**。别名条目上报的 `pattern` 仍是原始命令名，
   roost 按 pattern 首词解析命令名，于是判定「命令已被插件自己注册」并加载失败（loaded=false）。
   别名要写成独立的 `@p.command("别名")`。
3. **SDK 的 ready 不发 `listen` 字段**。不声明的话 roost 不会把非命令消息转发过来，
   `#星铁体力` 这类被动写法永远收不到。已在 `main.py` 里用 `StarrailPlugin` 子类覆盖 `_ready()` 补上
   `"listen": ["message"]`（不改 `roost_sdk.py`）。
4. **外部插件不能注册 AI 工具**。`subprocess.js` 明确只警告不生效，工具注册只对内核插件开放。
   所以对接 DeepSeek 不能走 tools，得另想办法（见阶段5）。
5. **插件放进 plugins 目录后不会自动出现**，要调 `POST /api/plugins/rescan`（需 `Content-Type: application/json`），
   或重启 roost。面板 `http://127.0.0.1:8080/api/status` 的 `plugins[].loaded/error` 是判断依据。
6. **改了插件代码，光 rescan 不会重载**。`loader.js:182` 明确 `if (this.loaded.has(id)) continue`——
   已加载的插件会被跳过；而插件目录被运行中的 `.venv` 进程占着，`Move-Item` 也移不动。
   可靠的更新方式是：拷完文件后 `Stop-Process` 掉插件子进程（`/api/status` 的 `pid`），
   它会 autoRestart（`subprocess.js:344`），重启即加载新代码。判断依据：日志里
   `外部插件就绪，注册 N 条命令` 的 N 变了。
7. **扫码接口 createQRLogin 与 queryQRLoginStatus 必须用同一个 `x-rpc-device_id`**。
   各生成一个不同的 UUID 会返回「请求失败，当前设备或网络环境存在风险」，看起来像风控，其实是设备不一致。
8. **插件不能事后主动推送**。`subprocess.js` 收到 `handled` 就 `#finish` 释放 `pending`，
   之后再发 `reply`/`push` 都因 seq 失效被静默丢弃。所以扫码这类异步流程只能做成「拉取式」：
   用户发命令查状态，而不是后台线程回调通知。
9. **被动监听分支必须走 `_reply`，不要直接 `m.reply(result.text)`**。
   直发 text 会把 `result.image` 丢掉，表现为「`/星铁扫码登录` 有图、`#星铁扫码登录` 没图」——
   用户几乎都用 `#`，等于全都没图。任何新增带图命令都要确认两条链路都能出图。
10. **米游社扫码的登录链接（`user.mihoyo.com/login-platform/mobile.html?...`）是给 App 扫的**，
    在浏览器里打开只会显示「请使用最新版本游戏或米游社APP扫码」，页面上没有二维码。
    别把它当兜底链接发给用户，二维码必须自己出图。米游社 App「扫一扫」支持从相册选图，
    所以「发二维码图 + 提示保存后用相册扫」是可行 UX。
11. **QQ 侧取图能力已验证可行**：`POST /v2/users/<openid>/files` 传 `{file_type:1, srv_send_msg:false, url}`，
    `api.pwmqr.com`、`api.qrserver.com`、`quickchart.io` 三个源都返回 200 + `file_info`（ttl 86400）。
    图发不出去时先怀疑自己没把 image 字段发出去，别急着换图床。
    诊断脚本 `scripts/probe_qq_media.py`（只上传不发送，需要 `QQ_OPENID` 环境变量）。
12. **`requests` 的 `resp.headers` 是 `CaseInsensitiveDict`，没有 `get_all`**（那是 urllib3 的接口）。
    扫码确认后要拿多个 `Set-Cookie`，必须走 `resp.cookies`（requests 已解析好）或
    `resp.raw.headers.get_all("Set-Cookie")`。写成 `resp.headers.get_all()` 会抛 `AttributeError`。
    回归用例：`scripts/test_qr_cookie.py`。
13. **插件抛异常且不回话时，消息会被 ai-chat 这类闲聊插件接走**，用户看到的是
    「机器人不认识这个命令」这种误导性回复，真实原因只在插件日志里。
    所以 `on_any_message` 里已加异常兜底：出错必回一句「命令处理出错了」并返回 True 认领消息。
    新增任何被动命令都要保持这个兜底。
14. **扫码拿到的凭证与 device_id 绑定**。`x-rpc-device-id` 每次随机生成的话，
    record 系列接口（`/game_record/app/hkrpg/api/note|index`）会被判定非本人设备。
    现在 device_id 随绑定一起落库（`user_bind.device_id`），后续请求沿用同一个。
    另外 `bind_service` 不能在 `__init__` 里缓存 `get_store()`，否则 init 切换 dataDir 后仍写旧库。
15. **record 接口的 10041 不能当签名错误处理**：签名错会返回 `-10001 invalid request`；
    10041 是账号/数据层面的拒绝（战绩未公开、只读权限、设备不匹配等），
    message 常为空，所以错误提示必须兜底带上 retcode。
16. **外部插件其实能发本地图片**（此前判断是错的，2026-11-07 实测推翻）：
    面板接口 `POST /api/qq/call` 支持 `method=uploadMedia`，`args` 里给 `fileData`（base64）
    即可上传本地 PNG（官方 `file_data` 上限 5MB，超出走分片），返回 `file_uuid` + `file_info`；
    再用 `method=sendC2C/sendGroup`、`msgType:7`、`content:' '`、`media:{file_info}` 发出富媒体。
    `args` 的位置参数约定是 `__target`（第一个）+ `__rest`（数组）+ 其余合成对象。
    所以图片不需要图床、不需要公网 URL。图床只作兜底（`h.uguu.se` 实测可用；
    catbox/litterbox/tmpfiles/0x0.st 在本网络不可用）。
17. **面板类数据可以完全不要 Cookie**：`api.mihomo.me/sr_info_parsed/{uid}?lang=chs`
    只要 UID 就能拿到角色/光锥/遗器（含主副词条）全量。代价是**只能拿到用户在
    米游社「角色展示」里放出来的角色**（实测 129 角色只解析到 8 个），帮助文案必须写明。
18. **群聊被动回复有硬额度**：5 分钟 / 5 次（错误码 40034128），单聊 60 分钟 / 4 次。
    一条命令只能回一次，图文必须合成一条富媒体，不要拆成多条。

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

### 双远端（GitHub 主仓 + Gitee 镜像）

```powershell
git push origin main    # GitHub  Silentlas/dsh-starrail-plugin
git push gitee  main    # Gitee   huang-yuhuan040216/dsh-starrail-plugin（国内访问用）
```

Gitee API 的两个坑（真机撞过）：
- **更新类接口只认 `application/x-www-form-urlencoded`**，发 JSON 一律 400。改仓库属性必须用表单编码。
- **创建接口会忽略 `private=false`**，账号默认建私有仓；可见性只能在创建后用 PATCH 表单改成公开。

## 六、多人协作

分工任务书在 `docs/tasks/`，接手前先读 `docs/tasks/00-总览与协作约定.md`。
要点：命令统一用 `core/registry.py` 注册（不改路由骨架）；每个模块目录只由对应负责人修改；
命令注册表里的 handler 签名统一 `func(req: Request) -> Result`，出图返回 `Result(media=Media(png=...))`。

## 七、开发与红线

开发顺序：数据结构 → 数据层 → 业务层 → 接入路由。每个功能必须验证：
正常返回 / Cookie 失效 / 网络失败 / 未绑定 / 群聊私聊区分 / 频率限制。

红线：
- 禁止往 stdout 写任何非协议内容
- 禁止日志打印完整 Cookie / authkey
- 禁止群聊接收或回显 Cookie
- 禁止硬编码接口 URL（统一 `core/api/config.py`）与数据目录
- 禁止凭记忆写米游社字段，一律查 UIGF 文档
- 禁止改 `roost_sdk.py`（官方文件，升级会被覆盖）

## 八、进度

- **阶段0 环境搭建** ✅ roost 插件骨架、DS 签名（真实接口已验证）、路由、SQLite、日志、频率限制、协议冒烟测试
- **阶段1 账号绑定** ✅ Cookie 手动绑定（自动拉 UID/区服/昵称）、校验、解绑、群聊拦截
  ｜ ✅ 米游社扫码登录（`#星铁扫码登录` → 二维码 → `#星铁扫码状态` 完成绑定）
  ｜ ⬜ Cookie 巡检
- **阶段2 练度查询** ⬜ 首页信息、角色详情、伤害预期
- **阶段3 抽卡分析** ⬜ authkey 解析、全量拉取、统计保底、UIGF 导出
- **阶段4 图片渲染** ⬜ Playwright 引擎与三类卡片
- **阶段5 AI 能力** ⬜ 自然语言解析、练度点评、账号诊断

**方案定稿（2026-11-07）**：详见 `docs/功能可行性与方案评估.md`。
要点：绑定以「只绑 UID」为默认、Cookie 为进阶；练度走 mihomo.me 免凭证；
遗器只做词条量化与面板总评（伤害引擎延后）；抽卡用用户 authkey；
图片用 Pillow 绘制 + `/api/qq/call` base64 直传；体力因 10041 排最后。
实施顺序：图片通道 → 练度 → 遗器评分 → 抽卡 → AI 点评 → 体力。

## 九、部署到 roost

插件目录名与 `plugin.json` 的 `id` 必须一致，roost 才会识别。
把整个项目目录（含 `core/`、`main.py`、`plugin.json`、`requirements.txt`）拷到
`C:\Users\admin\.dsh\dsh-roost\roost\plugins\dsh-starrail\`，
首次加载会自动建 `.venv` 装依赖，之后热重载（默认 2 秒）。

**最后更新**：2026-11-07
