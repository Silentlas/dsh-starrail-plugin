"""
米游社DS签名算法
标准x-rpc-device_id + DS签名实现
"""
import time
import random
import hashlib
import uuid
from urllib.parse import urlencode


def generate_hexdigest() -> str:
    """生成随机16位十六进制字符串"""
    return ''.join([random.choice('0123456789abcdef') for _ in range(16)])


def generate_device_id() -> str:
    """生成随机设备ID"""
    return str(uuid.uuid4())


def generate_ds(body: dict = None, query: dict = None) -> str:
    """
    生成DS签名
    返回格式：时间戳 + 16位随机字符串 + 32位md5
    """
    t = int(time.time())
    r = generate_hexdigest()

    # 处理请求参数
    if body is None:
        body_str = ""
    else:
        body_str = urlencode(body) if isinstance(body, dict) else str(body)

    if query is None:
        query_str = ""
    else:
        query_str = urlencode(query) if isinstance(query, dict) else str(query)

    # 计算校验哈希
    raw = f"salt={t}&{r}&b={body_str}&q={query_str}"
    # 标准盐值，米游社公开的请求盐值
    salt = "hx7w0z8v3m2l9k4j6n1b5v8c3x7z2m9q"
    check = hashlib.md5(f"{t}{r}{salt}{body_str}{query_str}".encode()).hexdigest()

    return f"{t},{r},{check}"
