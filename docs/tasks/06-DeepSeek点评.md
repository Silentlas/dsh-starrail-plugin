# T6 · DeepSeek 点评（AI 诊断）

> 负责人：**E** ｜ 前置：T3（角色模型）+ T4（评分结果） ｜ 工期：2 天
> 外部插件**不能把 AI 注册成 bot 工具**（`subprocess.js` 只警告不生效），所以只能由插件自己直连 API。

## 一、目标

在已有的结构化练度数据之上，用大模型产出一段**可读的点评**：

- `#星铁点评 <角色>`：单个角色的遗器/面板诊断 + 改进建议
- `#星铁诊断`：账号整体（角色池广度、练度分布、优先培养谁）

**定位**：模型只做「解释和排序」，**不做数值计算**。所有数字来自 T3/T4，prompt 里禁止让模型自己算面板或编数值。

## 二、要新建的文件

```
core/ai/
├── __init__.py
├── config.py      # API 地址、模型名、超时、额度
├── client.py      # HTTP 调用 + 重试 + 错误分类
├── prompt.py      # 把 model 对象压缩成 prompt（去噪、控 token）
├── comments.py    # 业务：点评/诊断的编排、缓存、额度
├── quota.py       # 每日额度（单用户 + 全局）
└── commands.py    # 命令注册
```

## 三、`config.py`

```python
"""
DeepSeek 接入配置
密钥来源优先级：roost 下发 config → 环境变量 DEEPSEEK_API_KEY
不要把密钥写进代码或提交到仓库
"""
AI_BASE = "https://api.deepseek.com"
AI_MODEL = "deepseek-chat"
AI_TIMEOUT = 30
AI_MAX_TOKENS = 800
AI_TEMPERATURE = 0.6

# 额度（超出后提示"今日额度已用完"）
QUOTA_USER_PER_DAY = 5
QUOTA_GLOBAL_PER_DAY = 300

# 点评结果缓存（同一 UID + 同一数据指纹，避免重复花钱）
COMMENT_TTL = 24 * 3600
```

密钥注入方式：`core/ai/client.py` 提供 `set_api_key(key)`，由 `main.py` 在 `init` 时从 roost config 里取（字段名约定 `deepseekApiKey`），取不到再读环境变量。**没有密钥时该模块的命令直接回「AI 点评未启用」**，不影响其他功能。

## 四、`client.py`

```python
"""DeepSeek Chat Completions 客户端（OpenAI 兼容协议）"""
from ..utils.logger import Logger

class AIError(Exception):
    """带人类可读消息的异常：额度不足 / 密钥无效 / 超时 / 内容审核"""

def chat(messages: list[dict], temperature: float = None, max_tokens: int = None) -> str:
    """返回模型回复正文；失败抛 AIError"""
```

要求：

- 标准 `POST {AI_BASE}/chat/completions`，`Authorization: Bearer <key>`
- 重试：仅对超时/5xx 重试一次（指数退避 2 秒），4xx 不重试
- 错误分类：`401` → 密钥无效；`429` → 今日额度不足；`400` → 请求被拒（多为内容审核）；超时 → 稍后再试
- **日志不打请求体全文**（含用户数据），只打 token 数与耗时

## 五、`prompt.py`（最关键的一环）

目标：把 `Character` + `PanelVerdict` 压成 **≤ 800 token** 的紧凑结构，且明确告诉模型「只用给的数据，不许自己算」。

```python
SYSTEM_PROMPT = """你是《崩坏：星穹铁道》的账号顾问，说话直接、具体、不客套。
规则：
1. 只能引用用户提供的面板数据，禁止编造未给出的数值、遗器或角色。
2. 不要计算伤害期望，不要声称某个配装是唯一最优解。
3. 每条建议必须指向具体部位或具体属性（例：脚部主词条建议换成速度）。
4. 输出 3~5 条，按优先级排序，总长不超过 200 字。
5. 数据不足时直接说"数据不足，无法判断"。
"""

def build_character_prompt(character: Character, verdict: PanelVerdict, relic_scores: list) -> list[dict]:
    """返回 messages"""
```

数据压缩规则：

- 只给：角色名/命途/元素/等级/命座、光锥（名/叠影/等级）、6 件遗器的「部位+套装+评分+有效词条名」、面板 6 个关键属性、T4 的短板列表
- **不给**：完整遗器对象、图标 URL、skills 明细（这些只会浪费 token）
- 数字统一保留 1 位小数，百分比统一格式

## 六、`comments.py` + `quota.py`

```python
"""AI 点评的业务编排"""
def comment_character(qq_id: str, uid: str, keyword: str) -> tuple[bool, str]:
    """返回 (是否成功, 文案)。内部负责：额度检查 → 数据 → prompt → 调用 → 缓存"""

def diagnose_account(qq_id: str, uid: str) -> tuple[bool, str]:
    """账号整体诊断：按「练度分布 → 优先培养建议」组织"""
```

额度实现用 SQLite（自己加表，别和 T5 抢）：

```sql
CREATE TABLE IF NOT EXISTS ai_quota (
    qq_id TEXT NOT NULL,
    day TEXT NOT NULL,          -- YYYY-MM-DD
    used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (qq_id, day)
);
CREATE TABLE IF NOT EXISTS ai_comment_cache (
    fingerprint TEXT PRIMARY KEY,   -- sha1(uid + 角色名 + 面板关键值)
    content TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
```

缓存指纹要包含**面板数据**（遗器变了就该重新点评），不是只按 UID 缓存。

## 七、命令与文案

| 命令 | 行为 | 群聊 |
|---|---|---|
| `#星铁点评 <角色>` | 单角色点评 | 可用（不含敏感信息） |
| `#星铁诊断` | 账号整体诊断 | 可用 |

输出示例：

```
遐蝶 · 点评
────────────
这套遗器的问题在躯干：主词条是攻击，但你的暴击率 54.6% 明显不够，暴伤 132% 吃不满。
1. 躯干主词条换成暴击率，预计把暴击率拉到 70% 以上。
2. 脚部副词条缺速度，建议刷出至少 4 点速度补到 134。
3. 两件评分 52/58 的遗器可以优先替换，主词条对的部位先别动。
（数据来自公开展示面板，仅供方向参考）
```

结尾必须带那句**免责说明**，并且不要出现「最强」「必刷」这类绝对化表述。

## 八、验收清单

- [ ] 无密钥时命令回「AI 点评未启用，请在配置里填入 deepseekApiKey」，其他命令不受影响
- [ ] `scripts/test_ai_prompt.py`：用 fixture 生成 prompt，断言 token 量（可用简单字符估算）与字段完整性；断言 prompt 里**不含**原始 JSON 全量
- [ ] 额度：同一用户第 6 次被拒；全局额度用尽后所有用户被拒
- [ ] 缓存命中：同一角色连续两次点评，第二次不发网络请求
- [ ] 401 / 429 / 超时 三种错误各有人话提示
- [ ] 模型输出里出现编造数值时（人工抽查 5 条），修正 prompt 而非改后处理
- [ ] 冒烟测试通过；日志无完整 prompt / 无密钥

## 九、风险

- **成本**：点评是付费调用。额度、缓存、去 token 三者缺一不可，否则公开群会被刷爆
- **合规**：点评内容不涉及账号安全信息，不要把 Cookie/UID 之外的隐私塞进 prompt；UID 可以给（用户自己可见）
- **不可靠**：模型可能说错话。文案层面保持「参考」语气，不承诺任何结论
- 千万不要让模型输出 JSON 再解析（不可靠），只取纯文本
