"""探针：验证米游社扫码登录两个接口是否可用（不需要 Cookie / DS 签名）"""
import json
import sys
import uuid

import requests

APP_ID = "bll8iq97cem8"
DEVICE_ID = str(uuid.uuid4()).upper()

HEADERS = {
    "Host": "passport-api.miyoushe.com",
    "Origin": "https://user.mihoyo.com",
    "Referer": "https://user.mihoyo.com/",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; M2101K9C Build/TKQ1.220829.002; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/108.0.5359.128 "
        "Mobile Safari/537.36 miHoYoBBS/2.71.1"
    ),
    "x-rpc-app_id": APP_ID,
    "x-rpc-device_id": DEVICE_ID,
    "Content-Type": "application/json",
}

BASE = "https://passport-api.miyoushe.com/account/ma-cn-passport/web"


def main():
    print("device_id:", DEVICE_ID)

    print("\n=== createQRLogin ===")
    r = requests.post(f"{BASE}/createQRLogin", headers=HEADERS, json={}, timeout=15)
    print("HTTP", r.status_code)
    try:
        body = r.json()
    except Exception:
        print("非 JSON:", r.text[:300])
        return
    print("retcode:", body.get("retcode"), "message:", body.get("message"))
    data = body.get("data") or {}
    print("url   :", data.get("url"))
    print("ticket:", data.get("ticket"))
    print("Set-Cookie:", r.headers.get("Set-Cookie"))

    ticket = data.get("ticket")
    if not ticket:
        return

    print("\n=== queryQRLoginStatus（未扫描）===")
    r2 = requests.post(f"{BASE}/queryQRLoginStatus", headers=HEADERS,
                       json={"ticket": ticket}, timeout=15)
    print("HTTP", r2.status_code)
    b2 = r2.json()
    print("retcode:", b2.get("retcode"), "message:", b2.get("message"))
    d2 = b2.get("data") or {}
    print("status:", d2.get("status"), " client_type:", d2.get("client_type"))

    print("\n=== 预期：status=Created 即链路正常 ===")


if __name__ == "__main__":
    main()
