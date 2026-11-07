"""
关键对照：同一 uid 在不同 Cookie 状态下打 note。
- 无 Cookie
- 假 Cookie
- 真 Cookie（已绑定）
如果三者都是 10041，说明拒绝来自 uid/角色数据本身，不是凭证；
如果无 Cookie 给 -100/10001，说明凭证是变量。
"""
import sqlite3
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

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def call(params, cookie):
    h = {
        "DS": generate_ds2(params=params),
        "x-rpc-app_version": "2.63.1",
        "x-rpc-client_type": "5",
        "x-rpc-device_id": "0DF5C84E-ECCF-441F-9188-06E95B1ABFD6",
        "Referer": "https://webstatic.mihoyo.com/",
        "User-Agent": UA,
    }
    if cookie:
        h["Cookie"] = cookie
    r = requests.get(NOTE, params=params, headers=h, timeout=15)
    d = r.json()
    return d.get("retcode"), (str(d.get("message") or d.get("msg") or ""))[:40]


def main():
    con = sqlite3.connect(DB)
    cookie, uid, region = con.execute("SELECT cookie, uid, region FROM user_bind LIMIT 1").fetchone()
    con.close()
    p = {"role_id": uid, "server": region}

    cases = [
        ("无 Cookie", None),
        ("假 Cookie", "ltoken_v2=abc; ltmid_v2=def; ltuid_v2=123; account_id=123"),
        ("真 Cookie", cookie),
    ]
    for name, ck in cases:
        code, msg = call(p, ck)
        print(f"  {name:12s} -> retcode={code} message={msg}")


if __name__ == "__main__":
    main()
