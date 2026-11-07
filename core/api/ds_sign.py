"""
米游社 DS 动态签名
规范来源：UIGF-org mihoyo-api-collection / 鉴权
https://uigf.org/zh/mihoyo-api-collection/other/authentication

DS1：x-rpc-client_type=2（安卓APP），salt 随版本变化（K2 salt）
DS2：x-rpc-client_type=5（其它/网页），使用 4X salt
本项目统一采用 client_type=5 + DS2，因为 4X salt 不随版本漂移，最稳定。
"""
import random
import time
import uuid
from hashlib import md5
from urllib.parse import quote

# 4X salt，配合 x-rpc-client_type=5 使用
SALT_4X = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
# K2 salt（仅 client_type=2 / DS1 使用；随米游社版本变化，容易失效）
SALT_K2 = "ZSHlXeQUBis52qD1kEgKt5lUYed4b7Bb"

CLIENT_TYPE = "5"
APP_VERSION = "2.63.1"

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def _build_query(params: dict | None) -> str:
    """URL 参数按字段名 ASCII 升序排列后拼接，空参返回空字符串"""
    if not params:
        return ""
    return "&".join(
        f"{k}={params[k]}" for k in sorted(params.keys(), key=lambda s: s.encode("utf-8"))
    )


def _build_body(body: dict | None) -> str:
    """请求体按字段名升序输出紧凑 JSON，空体返回空字符串"""
    if not body:
        return ""
    import json
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def generate_ds1(salt: str = SALT_K2) -> str:
    """DS1：t,r,md5(salt={salt}&t={t}&r={r})，r 为 6 位字母数字随机串"""
    t = int(time.time())
    r = "".join(random.choices(_LETTERS, k=6))
    main = f"salt={salt}&t={t}&r={r}"
    return f"{t},{r},{md5(main.encode('utf-8')).hexdigest()}"


def generate_ds2(params: dict | None = None, body: dict | None = None,
                 salt: str = SALT_4X) -> str:
    """
    DS2：t,r,md5(salt={salt}&t={t}&r={r}&b={body}&q={query})
    r 取 100000~200000 的随机整数，若命中 100000 则替换为 642367
    """
    t = int(time.time())
    r = random.randint(100001, 200000)  # 直接避开 100000，等价于规范里的特判
    q = _build_query(params)
    b = _build_body(body)
    main = f"salt={salt}&t={t}&r={r}&b={b}&q={q}"
    return f"{t},{r},{md5(main.encode('utf-8')).hexdigest()}"


def generate_ds(params: dict | None = None, body: dict | None = None,
                client_type: str = CLIENT_TYPE) -> str:
    """按 client_type 自动选择签名算法"""
    if client_type == "2":
        return generate_ds1()
    return generate_ds2(params=params, body=body)


def generate_device_id() -> str:
    """生成设备 ID（UUID4）"""
    return str(uuid.uuid4())


def generate_ds_header_urlencoded(params: dict | None = None) -> str:
    """备用：如需对参数值做 URL 编码的场景"""
    if not params:
        return ""
    return "&".join(
        f"{k}={quote(str(params[k]), safe='')}"
        for k in sorted(params.keys(), key=lambda s: s.encode("utf-8"))
    )
