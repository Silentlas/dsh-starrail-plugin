# AGENTS.md - 项目协作通用规则

> 所有参与本项目开发的AI模型、Agent、人类开发者，必须先阅读本文件，严格遵守以下规则。

---

## 一、项目基本信息

### 项目定位
- **项目名称**：dsh-starrail-plugin
- **目标**：基于 dsh-roost 插件平台开发《崩坏：星穹铁道》QQ机器人助手插件，深度集成 DeepSeek 大模型能力
- **部署场景**：公开QQ群，用户规模10~200人
- **最终形态**：开源发布（MIT协议）

### 核心原则
1. **快速落地优先**：优先复用成熟开源方案，避免从零造轮子
2. **分步交付**：每个阶段产出可运行、可验证的最小版本，禁止堆到最后一次性集成
3. **数据准确第一**：所有米游社接口数据必须与官方返回字段对齐，禁止编造或猜测字段
4. **安全合规**：Cookie等敏感信息禁止明文打印、禁止上传到日志，群聊禁止传递Cookie

---

## 二、技术栈约定

| 模块 | 技术选型 | 说明 |
|------|----------|------|
| 核心业务逻辑 | Python 3.10+ | 所有功能全部在Python侧实现 |
| HTTP服务 | FastAPI + Uvicorn | 本地127.0.0.1:8765提供接口 |
| DSH桥接层 | TypeScript | 极薄透传层，只做消息转发和基础频率限制 |
| 数据存储 | SQLite（Python内置sqlite3） | 零额外依赖 |
| 图片渲染 | Playwright + HTML/CSS模板 | 后续接入 |
| 米游社请求 | requests + DS签名封装 | 复用开源Python实现 |
| 大模型调用 | DeepSeek Python SDK | 原生调用 |
| 频率控制 | Python侧实现令牌桶 | 单用户每分钟2次，全群每分钟10次 |

---

## 三、目录结构约定

```
core/                 # Python核心业务逻辑
├── main.py           # FastAPI入口，提供HTTP接口
├── api/              # 米游社API封装
│   ├── client.py     # 请求封装、DS签名
│   ├── record.py     # 战绩接口
│   ├── character.py  # 角色详情
│   └── gacha.py      # 抽卡记录
├── bind/             # 账号绑定
│   ├── service.py
│   └── qrcode.py     # 扫码登录
├── character/       # 练度查询
│   ├── service.py
│   └── damage.py     # 伤害计算
├── gacha/            # 抽卡分析
│   ├── service.py
│   └── analyze.py
├── render/           # 图片渲染
│   ├── engine.py
│   └── templates/
├── ai/               # DeepSeek集成
│   ├── parser.py
│   └── review.py
└── utils/            # 工具
    ├── store.py      # SQLite存储
    ├── ratelimit.py
    ├── cache.py
    └── logger.py

bridge/               # DSH TypeScript桥接层（极薄透传）
├── index.ts
└── README.md

config/               # 配置文件
data/                 # 运行时数据（数据库、缓存）
templates/            # HTML渲染模板
assets/               # 静态资源
```

### 命名规范
- Python 文件/模块：snake_case，如 `record.py`
- 类名：PascalCase，如 `MhyClient`
- 函数/变量：snake_case
- 常量：UPPER_SNAKE_CASE，如 `REQUEST_INTERVAL`
- 命令前缀：统一使用 `#星铁` 开头，如 `#星铁绑定ck`、`#星铁体力`

## 三之二、运行与调试

**环境坑（必看）**：PATH 上的 `python` 是另一套运行时（3.13），没装本项目依赖。
依赖装在 `D:\Program Files\Python312\python.exe`，所有命令必须显式指定这个解释器。

```powershell
# 安装依赖（仅首次）
& "D:\Program Files\Python312\python.exe" -m pip install -r requirements.txt

# 启动服务（必须在项目根目录，入口用了相对导入）
Set-Location -LiteralPath "D:\Personal data\星铁机器人"
& "D:\Program Files\Python312\python.exe" -m core.main

# 健康检查
Invoke-RestMethod http://127.0.0.1:8765/health
```

**联调接口**：`POST http://127.0.0.1:8765/api/command`
请求体 `{qq_id, group_id?, command, args, is_group}`，返回 `{success, message, image?}`。

**米游社接口验证方法**：用假 Cookie 打真实接口，若返回业务错误码（如 -100 / 10001）说明
签名与请求头正确；若返回签名相关错误码则说明 DS 算法或 salt 有问题。

**接口规范来源**：`https://uigf.org/zh/mihoyo-api-collection/`（字段以此为准，禁止凭记忆写字段）。
当前用 `client_type=5` + 4X salt + DS2（该 salt 不随米游社版本漂移，最稳）；
`client_type=2` 的 K2 salt 随版本变化，容易失效，不要用。

---

## 四、Git提交规范

### 分支策略
- 主分支：`main`，保持可运行状态
- 开发分支：`dev`，所有功能从dev分支开发
- 功能分支：`feature/模块名-功能描述`，如 `feature/bind-qrcode-login`

### Commit message格式
```
<类型>: <描述>

[可选正文，详细说明变更内容]
```

类型枚举：
- `feat`：新功能
- `fix`：修复bug
- `refactor`：重构（不改变功能）
- `style`：代码格式调整
- `docs`：文档变更
- `chore`：构建、依赖、工具变更
- `test`：测试相关

示例：
```
feat(bind): 实现米游社扫码登录流程
- 生成登录二维码
- 轮询扫码状态
- 自动获取并存储Cookie
```

---

## 五、开发流程要求

### 单模块开发顺序
1. 先写数据结构定义（dataclass / 类型）
2. 再写数据层逻辑（API 调用、字段清洗）
3. 再写业务逻辑（缓存、频率控制、错误处理）
4. 最后接入命令入口和渲染

### 必须验证的场景
每个功能开发完成后，必须验证以下场景：
1. 正常返回数据
2. Cookie失效/过期
3. 网络请求失败
4. 用户未绑定账号
5. 群聊/私聊场景区分
6. 频率限制触发

### 禁止事项
- 禁止在日志中打印完整Cookie、authkey、用户敏感信息
- 禁止在群聊场景下接收/回复Cookie相关内容
- 禁止硬编码接口URL，统一放在 `core/api/config.py`
- 禁止在代码中写死用户ID、测试QQ号
- 禁止引入未经验证的重型依赖（尤其是原生编译模块）
- 禁止凭记忆写米游社返回字段，一律以 UIGF 文档为准

---

## 六、任务交接规则

### 新任务开始前
必须先读取以下文件，对齐上下文：
1. 本文件（AGENTS.md）
2. README.md（项目整体介绍）
3. 对应模块目录下的现有代码

### 完成任务后
必须输出：
1. 变更的文件列表
2. 实现的功能点
3. 已知的限制或待优化项
4. 测试验证结果

### 禁止行为
- 禁止在未了解现有代码结构的情况下，直接重写整个模块
- 禁止删除用户已有的代码或文件，除非明确要求
- 禁止跳过错误处理直接返回数据
- 禁止编造不存在的接口字段、返回数据

---

## 七、当前开发阶段

### 阶段0：环境搭建 ✅ 完成
- [x] Python 工程骨架（FastAPI 服务 + SQLite + 日志 + 频率限制）
- [x] DS 签名（DS2 / 4X salt）与请求头规范，已用真实接口验证
- [x] 命令路由层（`#星铁帮助` / `绑定ck` / `解绑` / `体力`）
- [ ] DSH TypeScript 桥接层（`bridge/`，尚未编写）

### 阶段1：账号绑定体系（进行中）
- [x] Cookie 手动绑定（自动拉取 UID / 区服 / 昵称）
- [x] Cookie 校验、解绑、群聊拦截
- [ ] 米游社扫码登录
- [ ] Cookie 有效性定期巡检

### 阶段2：练度查询
- [ ] 首页信息（角色列表、账号总览）
- [ ] 角色详情（技能、光锥、遗器、面板）
- [ ] 伤害预期计算

### 阶段3：抽卡分析
- [ ] 抽卡链接解析与 authkey 提取
- [ ] 全量记录拉取与增量更新
- [ ] 统计和保底计算、UIGF 导出

### 阶段4：图片渲染
- [ ] Playwright 渲染引擎
- [ ] 角色练度卡
- [ ] 账号总览卡
- [ ] 抽卡分析图

### 阶段5：AI能力集成
- [ ] 自然语言指令解析
- [ ] 练度AI点评
- [ ] 账号综合诊断

---

## 八、参考资源

- DSH插件开发文档：待补充
- 米游社API参考：开源项目 `mihoyo-api` 系列
- 星铁UI参考：Yunzai-Bot 星铁插件
- 抽卡数据标准：UIGF规范

---

**最后更新**：2026-11-07
