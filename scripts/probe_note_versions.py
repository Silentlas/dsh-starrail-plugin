"""
10041 继续排查：试 client_type=2 + DS1(K2 salt)，以及若干 app_version。
已知：假 uid 返回 10102（未公开），真 uid 返回 10041 → 说明校验落在具体角色数据上。
"""
import sqlite3
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.api.ds_sign import SALT_K2, generate_ds1, generate_ds2, SALT_4X  # noqa: E402

DB = Path(r"C:\Users\admin\.dsh\dsh-roost\roost\plugins\dsh-starrail\data\starrail.db")
NOTE = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"

UA = ("Mozilla/5.0 (Linux; Android 12; Mi 10) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 miHoYoBBS/2.63.1")


def call(params, cookie, ct, ver, ds):
    headers = {
        "Cookie": cookie,
        "DS": ds,
        "x-rpc-app_version": ver,
        "x-rpc-client_type": ct,
        "x-rpc-device_id": "5f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
        "x-rpc-language": "zh-cn",
        "x-rpc-device_model": "Mi 10",
        "x-rpc-device_name": "Mi 10",
        "x-rpc-sys_version": "12",
        "User-Agent": UA,
        "Referer": "https://app.mihoyo.com/",
    }
    r = requests.get(NOTE, params=params, headers=headers, timeout=15)
    d = r.json()
    return d.get("retcode"), (str(d.get("message") or d.get("msg") or ""))[:40]


def main():
    con = sqlite3.connect(DB)
    cookie, uid, region = con.execute("SELECT cookie, uid, region FROM user_bind LIMIT 1").fetchone()
    con.close()
    p = {"role_id": uid, "server": region}

    print("== client_type=2 + DS1(K2) ==")
    for ver in ("2.63.1", "2.40.1", "2.11.1"):
        code, msg = call(p, cookie, "2", ver, generate_ds1(SALT_K2))
        print(f"  ct2 ver={ver:8s} -> retcode={code} message={msg}")

    print("\n== client_type=5 + DS2 换 app_version ==")
    for ver in ("2.40.1", "2.50.1", "2.71.0", "2.63.1"):
        code, msg = call(p, cookie, "5", ver, generate_ds2(params=p, body=None, salt=SALT_4X))
        print(f"  ct5 ver={ver:8s} -> retcode={code} message={msg}")


if __name__ == "__main__":
    main()
