"""
排查游戏扫码 query 返回「当前设备或网络环境存在风险」。
变量：device 是否复用、是否带 x-rpc-device-id 头、UA、查询时序。
"""
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
APP_ID = 8
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 miHoYoBBS/2.76.1")
UA_MOBILE = ("Mozilla/5.0 (Linux; Android 12; Mi 10) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36 miHoYoBBS/2.67.1")


def call(url, body, headers):
    r = requests.post(url, json=body, headers=headers, timeout=15)
    d = r.json()
    return d.get("retcode"), str(d.get("message") or "")[:60], d.get("data")


def run(label, device, headers, ua):
    h = dict(headers, **{"Content-Type": "application/json", "User-Agent": ua})
    code, msg, data = call(FETCH, {"app_id": APP_ID, "device": device}, h)
    if code != 0:
        print(f"  [{label}] fetch -> {code} {msg}")
        return
    ticket = (data or {}).get("url", "")[-24:]
    time.sleep(2)
    code2, msg2, data2 = call(QUERY, {"app_id": APP_ID, "device": device, "ticket": ticket}, h)
    status = (data2 or {}).get("status")
    print(f"  [{label}] fetch=0 query -> retcode={code2} status={status} message={msg2}")


def main():
    stable = str(uuid.uuid5(uuid.NAMESPACE_DNS, "dsh-starrail-bot")).upper()
    print("稳定 device:", stable)

    run("A 仅 body device", stable, {}, UA)
    run("B +x-rpc-device-id 头", stable, {"x-rpc-device_id": stable}, UA)
    run("C 新 device", str(uuid.uuid4()).upper(), {"x-rpc-device_id": "x"}, UA)
    run("D 移动端 UA", stable, {"x-rpc-device_id": stable}, UA_MOBILE)
    run("E 无 app_id 头", stable, {"x-rpc-app_id": ""}, UA)


if __name__ == "__main__":
    main()
