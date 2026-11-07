"""
星穹铁道接口配置
数据来源规范：UIGF-org mihoyo-api-collection
"""
# 崩坏：星穹铁道 国服标识
GAME_BIZ = "hkrpg_cn"
# 国服常用区服标识
DEFAULT_REGION = "prod_gf_cn"

# 账号类接口（api-takumi.mihoyo.com）
BINDING_API = "https://api-takumi.mihoyo.com"
# 游戏记录类接口（api-takumi-record.mihoyo.com）
RECORD_API = "https://api-takumi-record.mihoyo.com"

# 通过 LToken 获取绑定的游戏账号
URL_GET_ROLES_BY_COOKIE = f"{BINDING_API}/binding/api/getUserGameRolesByCookie"

# 星铁首页（玩家基础信息 + 角色列表）
URL_INDEX = f"{RECORD_API}/game_record/app/hkrpg/api/index"

# 星铁实时便笺（开拓力、派遣、每日实训）
# 注：UIGF 文档未收录该接口，但为社区广泛使用的稳定端点
URL_NOTE = f"{RECORD_API}/game_record/app/hkrpg/api/note"

# 请求间隔下限（秒），避免触发风控
REQUEST_INTERVAL = 1.5

# 查询结果本地缓存时长（秒）
CACHE_TTL = 15 * 60

# 首次请求超时（秒）
REQUEST_TIMEOUT = 10
