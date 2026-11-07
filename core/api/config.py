"""
米游社API配置
"""
# 星铁游戏ID
GAME_ID = "hkrpg"
REGION = "prod_gf_cn"

# API基础地址
COIN_API = "https://api-takumi.mihoyo.com"
RECORD_API = "https://api-takumi-record.mihoyo.com"

# 请求头默认值
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://webstatic.mihoyo.com/",
    "x-rpc-client_type": "5",
    "x-rpc-app_version": "2.63.1",
    "x-rpc-language": "zh-cn",
}

# 请求间隔（秒），避免触发风控
REQUEST_INTERVAL = 1.5

# 缓存有效期（秒）
CACHE_TTL = 15 * 60  # 15分钟
