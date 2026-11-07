"""
对照 FufuLauncher（能正常跑游戏扫码的启动器）的请求头，验证我们的 fetch/query 是否被接受。
重点变量：x-rpc-device_id 头、device_fp、client_type=2、app_version、DS 盐。
"""
import hashlib
import json
import random
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests  # noqa: E402

FETCH = "https://api-sdk.mihoyo.com/hkrpg_cn/combo/panda/qrcode/fetch"
QUERY = "https://api-sdk.mihoyo.com/hkrpg_cn/combo/panda/qrcode/query"
CAPTURE_SALT = "dDIQHbKOdaPaLuvQKVzUzqdeCaxjtaPV"
SALT_4X = "xVv4Qu54lUKrEYFZkJhB8cuOh9Asafs"  # 占位，实际下面用真实 4X
from core.api.ds_sign import SALT_4X as REAL_4X  # noqa: E402

UA = "Mozilla/5.0 miHoYoBBS/2.90.1 Capture/2.2.0"


def ds(salt: str, body: dict) -> str:
    t = int(time.time())
    r = random.randint(100001, 200000)
    b = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    s = f"salt={salt}&t={t}&r={r}&b={b}&q="
    return f"{t},{r},{hashlib.md5(s.encode()).hexdigest()}"


def device16() -> str:
    return uuid.uuid4().hex[:16].upper()


def device_fp(device_id: str) -> str:
    payload = {
        "device_id": device_id,
        "seed_id": uuid.uuid4().hex[:16],
        "seed_time": int(time.time()),
        "platform": "2",
        "device_fp": "",
        "app_name": "bbs_cn",
    }
    return hashlib.md5(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def build_headers(device_id: str, ds_value: str) -> dict:
    return {
        "x-rpc-app_id": "bll8iq97cem8",
        "x-rpc-device_id": device_id,
        "x-rpc-device_fp": device_fp(device_id),
        "x-rpc-client_type": "2",
        "x-rpc-app_version": "2.90.1",
        "x-rpc-game_biz": "bbs_cn",
        "x-rpc-sdk_version": "2.90.1",
        "x-rpc-account_version": "2.90.1",
        "x-rpc-device_model": "Mi 14",
        "x-rpc-device_name": "Mihoyo Capture",
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "zh-cn",
        "Content-Type": "application/json",
        "DS": ds_value,
    }


def run(label, headers_fn):
    device_id = device16()
    body = {"app_id": 8, "device": device_id}
    h = headers_fn(device_id, body)
    r = requests.post(FETCH, json=body, headers=h, timeout=15).json()
    if r.get("retcode") != 0:
        print(f"  [{label}] fetch -> {r.get('retcode')} {r.get('message')}")
        return
    ticket = r["data"]["url"][-24:]
    body2 = {"app_id": 8, "device": device_id, "ticket": ticket}
    h2 = headers_fn(device_id, body2)
    time.sleep(1)
    q = requests.post(QUERY, json=body2, headers=h2, timeout=15).json()
    print(f"  [{label}] fetch=0 query -> retcode={q.get('retcode')} stat={(q.get('data') or {}).get('stat')} "
          f"message={str(q.get('message') or '')[:40]}")


def main():
    print("== 无 DS，仅补 Fufu 头 ==")
    run("A 补头无DS", lambda d, b: {k: v for k, v in build_headers(d, "").items() if k != "DS"})

    print("== DS 用 4X 盐 ==")
    run("B DS(4X)", lambda d, b: build_headers(d, ds(REAL_4X, b)))

    print("== DS 用 capture 盐 ==")
    run("C DS(capture)", lambda d, b: build_headers(d, ds(CAPTURE_SALT, b)))

    print("== 老头（我们当前实现）==")
    run("D 极简头", lambda d, b: {"Content-Type": "application/json", "x-rpc-app_id": "bll8iq97cem8",
                              "User-Agent": UA})


if __name__ == "__main__":
    main()
