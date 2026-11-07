"""
探针：星铁游戏登录二维码（米游社 App 扫码）
目的：确认 hkrpg 侧 qrcode fetch/query 端点、字段结构，以及扫码确认后 payload 里有什么。
用法：python scripts/probe_game_qr.py      # 后台跑，日志写到 scripts/game_qr_log.txt
"""
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "scripts" / "game_qr_log.txt"

CANDIDATES = [
    "https://hkrpg-sdk.mihoyo.com/hkrpg_cn/combo/panda/qrcode",
    "https://api-sdk.mihoyo.com/hkrpg_cn/combo/panda/qrcode",
]

DEVICE = "7C2A9D31-5B77-4A0E-8C0F-1D2E3F4A5B6C"
HEADERS = {
    "Content-Type": "application/json",
    "x-rpc-app_id": "bll8iq97cem8",
    "x-rpc-device_id": DEVICE,
    "x-rpc-client_type": "2",
    "x-rpc-app_version": "2.71.1",
    "User-Agent": "okhttp/4.9.3",
}
APP_ID = "5"


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def post(url, body):
    r = requests.post(url, json=body, headers=HEADERS, timeout=15)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"_raw": r.text[:120]}


def main():
    LOG.write_text("", encoding="utf-8")

    base = None
    for b in CANDIDATES:
        code, d = post(b + "/fetch", {"app_id": APP_ID, "device": DEVICE})
        log(f"fetch {b} -> http={code} retcode={d.get('retcode')} message={d.get('message')}")
        log("fetch data=" + json.dumps(d.get("data"), ensure_ascii=False)[:300])
        if d.get("retcode") == 0:
            base = b
            break

    if not base:
        log("所有候选端点 fetch 都失败，终止")
        return

    qr_url = d["data"]["url"]
    from urllib.parse import parse_qs, urlparse
    ticket = (parse_qs(urlparse(qr_url).query).get("ticket") or [""])[0]
    log(f"ticket={ticket}")
    log(f"qr_url={qr_url}")
    log("qr_image=" + "https://api.pwmqr.com/qrcode/create/?url=" + quote(qr_url, safe=""))

    seen = None
    deadline = time.time() + 300
    while time.time() < deadline:
        code, q = post(base + "/query", {"app_id": APP_ID, "device": DEVICE, "ticket": ticket})
        if q.get("retcode") != 0:
            log(f"query 失败 retcode={q.get('retcode')} message={q.get('message')}")
            time.sleep(3)
            continue
        status = (q.get("data") or {}).get("status")
        if status != seen:
            log(f"status={status} keys={list((q.get('data') or {}).keys())}")
            seen = status
        payload = (q.get("data") or {}).get("payload")
        if payload:
            log("payload keys=" + str(list(payload.keys())))
            for k in ("uid", "token", "region", "account_id", "proto"):
                if k in payload:
                    v = payload[k]
                    if k == "token":
                        v = f"len={len(v)}"
                    log(f"  payload[{k}]={v}")
            raw = payload.get("raw")
            if raw:
                try:
                    raw_obj = json.loads(raw)
                    log("raw keys=" + str(list(raw_obj.keys())))
                    for k, v in raw_obj.items():
                        if k == "token":
                            v = f"len={len(str(v))}"
                        log(f"  raw[{k}]={v}")
                except Exception:
                    log("raw 解析失败")
            if status == "Confirmed":
                log("已确认，结束轮询")
                return
        time.sleep(3)


if __name__ == "__main__":
    main()
