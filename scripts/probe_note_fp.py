"""
最后一组对照：note 端点补齐新版米游社 App 的头部（device_fp / channel appstore / page / app_id）。
若仍 10041，则确认是账号侧凭证不足，与请求头无关。
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
from core.api.ds_sign import SALT_4X, generate_ds2, generate_ds1, SALT_K2  # noqa: E402

DB = Path(r"C:\Users\admin\.dsh\dsh-roost\roost\data\bots\main\plugins\dsh-starrail\starrail.db")
NOTE = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"
INDEX = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/index"

UA_APP = ("Mozilla/5.0 (Linux; Android 12; Mi 10) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 miHoYoBBS/2.63.1")


def rand_fp(n=32):
    return "".join(random.choices(string.hexdigits.lower()[:16], k=n))


def main():
    con = sqlite3.connect(DB)
    cookie, uid, region = con.execute("SELECT cookie, uid, region FROM user_bind LIMIT 1").fetchone()
    con.close()
    p = {"role_id": uid, "server": region}

    base = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "User-Agent": UA_APP,
        "Referer": "https://app.mihoyo.com",
        "x-rpc-app_version": "2.63.1",
        "x-rpc-channel": "appstore",
        "x-rpc-client_type": "5",
        "x-rpc-device_id": "0DF5C84E-ECCF-441F-9188-06E95B1ABFD6",
        "x-rpc-device_model": "Mi 10",
        "x-rpc-device_name": "Mi 10",
        "x-rpc-sys_version": "12",
        "x-rpc-platform": "android",
        "x-rpc-app_id": "bll8iq97cem8",
        "x-rpc-page": "v4.2.2-ys_#/ys/daily",
        "Cookie": cookie,
    }

    variants = [
        ("+device_fp", dict(base, **{"x-rpc-device_fp": rand_fp()})),
        ("+fp+DS", dict(base, **{"x-rpc-device_fp": rand_fp(), "DS": generate_ds2(params=p)})),
        ("ct2+fp+DS1", dict(base, **{"x-rpc-client_type": "2", "x-rpc-device_fp": rand_fp(),
                                     "DS": generate_ds1(SALT_K2)})),
        ("ct5+DS2 无其余头", {"Cookie": cookie, "DS": generate_ds2(params=p),
                          "x-rpc-app_version": "2.63.1", "x-rpc-client_type": "5",
                          "x-rpc-device_id": "0DF5C84E-ECCF-441F-9188-06E95B1ABFD6",
                          "User-Agent": UA_APP, "Referer": "https://webstatic.mihoyo.com/"}),
    ]
    for name, h in variants:
        try:
            r = requests.get(NOTE, params=p, headers=h, timeout=15)
            d = r.json()
            code, msg = d.get("retcode"), str(d.get("message") or "")[:40]
        except Exception as e:
            code, msg = "EXC", str(e)[:40]
        print(f"  note {name:20s} -> retcode={code} message={msg}")

    # index 也带上 device_fp 试一次
    try:
        r = requests.get(INDEX, params=p, headers=dict(base, **{"x-rpc-device_fp": rand_fp(),
                                                                 "DS": generate_ds2(params=p)}), timeout=15)
        d = r.json()
        print(f"  index +fp+DS          -> retcode={d.get('retcode')} message={str(d.get('message') or '')[:40]}")
    except Exception as e:
        print("  index +fp+DS          -> EXC", str(e)[:40])


if __name__ == "__main__":
    main()
