"""
按 Starward 的实际实现补齐 note 请求头：X-Request-With: com.mihoyo.hyperion + x-rpc-device_fp。
device_fp 先试随机值，再试从 public-data-api 真实申请一个。
"""
import random
import sqlite3
import string
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.api.ds_sign import generate_ds2  # noqa: E402

DB = Path(r"C:\Users\admin\.dsh\dsh-roost\roost\data\bots\main\plugins\dsh-starrail\starrail.db")
NOTE = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"
INDEX = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/index"
FP_API = "https://public-data-api.mihoyo.com/device-fp/api/getFp"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def rand_hex(n):
    return "".join(random.choices("0123456789abcdef", k=n))


def get_real_fp(device_id):
    payload = {
        "seed_id": rand_hex(16),
        "device_id": device_id,
        "platform": "2",
        "seed_time": 1720000000000,
        "ext_fields": '{"proxyStatus":"0","isRoot":"0","romCapacity":"512","deviceName":"Mi10",'
                      '"webglReportHash":"1","magic":"1"}',
        "app_name": "bbs_cn",
        "bbs_device_id": device_id,
        "device_fp": rand_hex(13),
    }
    try:
        r = requests.post(FP_API, json=payload, timeout=15)
        d = r.json()
        return (d.get("data") or {}).get("device_fp"), d.get("retcode")
    except Exception as e:
        return None, str(e)[:40]


def call(url, params, cookie, headers):
    h = dict(headers)
    h["Cookie"] = cookie
    h["DS"] = generate_ds2(params=params)
    r = requests.get(url, params=params, headers=h, timeout=15)
    d = r.json()
    return d.get("retcode"), str(d.get("message") or "")[:40], d.get("data")


def main():
    con = sqlite3.connect(DB)
    cookie, uid, region, dev = con.execute(
        "SELECT cookie, uid, region, device_id FROM user_bind LIMIT 1").fetchone()
    con.close()
    p = {"role_id": uid, "server": region}

    base = {
        "x-rpc-app_version": "2.63.1",
        "x-rpc-client_type": "5",
        "x-rpc-device_id": dev,
        "Referer": "https://webstatic.mihoyo.com/",
        "User-Agent": UA,
    }

    print("== 试 X-Request-With / device_fp ==")
    fp_real, code = get_real_fp(dev)
    print(f"  getFp -> retcode={code} fp={fp_real}")

    variants = [
        ("+X-Request-With", dict(base, **{"X-Request-With": "com.mihoyo.hyperion"})),
        ("+X-Request-With+fp随机", dict(base, **{"X-Request-With": "com.mihoyo.hyperion",
                                            "x-rpc-device_fp": rand_hex(13)})),
        ("+X-Request-With+fp真实", dict(base, **{"X-Request-With": "com.mihoyo.hyperion",
                                            "x-rpc-device_fp": fp_real or rand_hex(13)})),
    ]
    for name, h in variants:
        code, msg, data = call(NOTE, p, cookie, h)
        brief = "" if not data else f" stamina={data.get('current_stamina')}/{data.get('max_stamina')}"
        print(f"  note {name:24s} -> retcode={code} message={msg}{brief}")

    code, msg, _ = call(INDEX, p, cookie, dict(base, **{
        "X-Request-With": "com.mihoyo.hyperion", "x-rpc-device_fp": fp_real or rand_hex(13)}))
    print(f"  index +hyperion+fp        -> retcode={code} message={msg}")


if __name__ == "__main__":
    main()
