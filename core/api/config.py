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

# ---- 扫码登录（passport-api.miyoushe.com）----
# 规范：https://uigf.org/zh/mihoyo-api-collection/hoyolab/login/qrcode_hoyolab.html
# 这两个接口不需要 Cookie，也不需要 DS 签名，只要 x-rpc-app_id + x-rpc-device_id
PASSPORT_API = "https://passport-api.miyoushe.com"
URL_QR_CREATE = f"{PASSPORT_API}/account/ma-cn-passport/web/createQRLogin"
URL_QR_QUERY = f"{PASSPORT_API}/account/ma-cn-passport/web/queryQRLoginStatus"
QR_APP_ID = "bll8iq97cem8"
QR_REFERER = "https://user.mihoyo.com/"

# 扫码状态
QR_STATUS_CREATED = "Created"
QR_STATUS_SCANNED = "Scanned"
QR_STATUS_CONFIRMED = "Confirmed"
QR_RETCODE_EXPIRED = -3501
QR_RETCODE_CANCELLED = -3505

# 二维码有效期（秒），米游社给的是约 5 分钟，留出余量
QR_TTL = 240
# 轮询间隔（秒），太密集会被风控
QR_POLL_INTERVAL = 3

# ---- 游戏登录二维码（combo/panda）----
# 扫的是「登录游戏」的码，换到的是 stoken / ltoken(v1) / cookie_token，
# 战绩类接口（note、index、角色练度）只认这套凭证
GAME_QR_APP_ID = 8  # 崩坏：星穹铁道
URL_GAME_QR_FETCH = "https://api-sdk.mihoyo.com/hkrpg_cn/combo/panda/qrcode/fetch"
URL_GAME_QR_QUERY = "https://api-sdk.mihoyo.com/hkrpg_cn/combo/panda/qrcode/query"
URL_S_TOKEN_BY_GAME_TOKEN = "https://api-takumi.mihoyo.com/account/ma-cn-session/app/getTokenByGameToken"
URL_LTOKEN_BY_STOKEN = "https://passport-api.miyoushe.com/account/auth/api/getLTokenBySToken"
URL_COOKIE_BY_STOKEN = "https://passport-api.miyoushe.com/account/auth/api/getCookieAccountInfoBySToken"
URL_STOKEN_V2_BY_V1 = "https://passport-api.miyoushe.com/account/ma-cn-session/app/getTokenBySToken"

# 把登录链接渲染成二维码图片的公网服务（roost 只能发远程图片 URL，本地文件发不出去）
# {data} 会被替换成 urlencode 后的登录链接
QR_IMAGE_API = "https://api.pwmqr.com/qrcode/create/?url={data}"

# 请求间隔下限（秒），避免触发风控
REQUEST_INTERVAL = 1.5

# 查询结果本地缓存时长（秒）
CACHE_TTL = 15 * 60

# 首次请求超时（秒）
REQUEST_TIMEOUT = 10

# ---- 频率限制（每分钟次数，0 表示该维度不限流）----
# 调试期单用户先放开；公开群上线前再根据实际负载调回来
RATE_LIMIT_USER_PER_MIN = 0
RATE_LIMIT_GROUP_PER_MIN = 10
