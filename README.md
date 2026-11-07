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

- TypeScript + DSH 插件规范
- Puppeteer 图片渲染
- SQLite 数据存储
- DeepSeek 大模型 API

## 快速开始

### 环境要求
- Node.js 18+
- dsh-roost 运行环境
- Chrome/Chromium (用于图片渲染)

### 安装
```bash
# 克隆仓库
git clone https://github.com/Silentlas/dsh-starrail-plugin.git
cd dsh-starrail-plugin

# 安装依赖
npm install

# 编译
npm run build
```

## 项目结构

```
dsh-starrail-plugin/
├── src/                # 源代码
│   ├── index.ts        # 插件入口
│   ├── api/            # 米游社API封装
│   ├── bind/           # 账号绑定模块
│   ├── character/      # 练度查询模块
│   ├── gacha/          # 抽卡分析模块
│   ├── render/         # 图片渲染模块
│   ├── ai/             # DeepSeek AI集成
│   └── utils/          # 工具函数
├── templates/          # HTML模板
├── assets/             # 静态资源
├── package.json
└── tsconfig.json
```

## 免责声明

- 本项目仅作学习交流使用，禁止商用
- 游戏素材版权归米哈游所有
- 绑定Cookie存在账号风险，请谨慎使用
- 本项目不对任何账号封禁或数据泄露负责

## License

[MIT](LICENSE)
