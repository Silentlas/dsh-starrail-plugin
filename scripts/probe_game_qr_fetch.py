"""
验证星铁游戏登录二维码取码接口是否可用（不需要扫码）。
候选 host：api-sdk.mihoyo.com / hkrpg-sdk.mihoyo.com，app_id=8。
"""
import sys
import uuid

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEVICE = str(uuid.uuid4()).upper()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 miHoYoBBS/2.76.1")

CANDIDATES = [
    "https://api-sdk.mihoyo.com/hkrpg_cn/combo/panda/qrcode/fetch",
    "https://hkrpg-sdk.mihoyo.com/hkrpg_cn/combo/panda/qrcode/fetch",
]


def main():
    for url in CANDIDATES:
        for app_id in (8, 5):
            try:
                r = requests.post(url, json={"app_id": app_id, "device": DEVICE},
                                  headers={"Content-Type": "application/json",
                                           "x-rpc-app_id": "bll8iq97cem8",
                                           "User-Agent": UA}, timeout=15)
                d = r.json()
                print(f"{url}\n  app_id={app_id} -> HTTP {r.status_code} retcode={d.get('retcode')} "
                      f"message={str(d.get('message') or '')[:40]}")
                data = d.get("data") or {}
                if data:
                    print(f"    url={str(data.get('url'))[:100]}")
                    print(f"    ticket={data.get('ticket')}")
            except Exception as e:
                print(f"{url} app_id={app_id} -> EXC {e}")


if __name__ == "__main__":
    main()
