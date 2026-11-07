# dsh-starrail-plugin

基于 dsh-roost 插件平台开发的《崩坏：星穹铁道》QQ机器人助手插件，深度集成 DeepSeek 大模型能力。

## 核心功能

### 已规划功能
- ✅ **账号绑定体系**：米游社扫码登录 + 手动Cookie绑定双模式
- ✅ **练度查询**：角色面板、遗器详情、光锥信息、伤害预期计算
- ✅ **抽卡分析**：全卡池记录统计、保底进度计算、UIGF格式导出
- ✅ **图片渲染**：账号总览卡、角色练度卡、抽卡分析图
- ✅ **AI增强能力**：自然语言指令解析、练度AI点评、抽卡建议、账号综合诊断
- ✅ **群控风控**：单用户/全群双层频率限制、请求间隔、本地缓存

### 后续迭代
- 深渊/虚构叙事战绩查询
- 米游币自动签到
- 角色培养材料计算
- 代理池/签名轮换高级风控
- 国际服(Hoyolab)支持

## 技术栈

- **定位**：dsh-roost「外部插件」，独立子进程运行，NDJSON (stdin/stdout) 协议
- **语言**：Python（官方 `roost_sdk.py`）
- **存储**：SQLite，数据落在 roost 下发的插件专属 `dataDir`
- **图片渲染**：Playwright（后续接入）
- **依赖**：`requirements.txt` 由 roost 首次加载时自动装进插件专属 `.venv`

## 快速开始

### 安装
```bash
git clone https://github.com/Silentlas/dsh-starrail-plugin.git
```

把整个目录拷贝到 roost 插件目录，目录名必须与 `plugin.json` 的 `id` 一致：

```
<roost>/plugins/dsh-starrail/
├── plugin.json
├── main.py
├── requirements.txt
├── core/
└── ...
```

首次加载 roost 会自动建 `.venv` 并安装依赖，之后热重载生效。

### 本地调试（不连 QQ）
```bash
python scripts/smoke_test.py
```
模拟 roost 往 stdin 喂 NDJSON，校验 ready、各命令分支与 stdout 协议纯净度。

## 项目结构

```
main.py             # roost 插件入口（协议层，只做转发）
roost_sdk.py        # 官方 Python SDK（勿改）
plugin.json         # 插件元信息
core/
├── router.py       # 命令路由（与传输无关）
├── api/            # 米游社接口：DS签名、请求封装、字段清洗
├── bind/           # 账号绑定
├── character/      # 练度查询
├── gacha/          # 抽卡分析
├── render/         # 图片渲染
├── ai/             # DeepSeek 集成
└── utils/          # 日志脱敏、SQLite、频率限制
scripts/
└── smoke_test.py   # 协议冒烟测试
```

## 免责声明

- 本项目仅作学习交流使用，禁止商用
- 游戏素材版权归米哈游所有
- 绑定Cookie存在账号风险，请谨慎使用
- 本项目不对任何账号封禁或数据泄露负责

## License

[MIT](LICENSE)
