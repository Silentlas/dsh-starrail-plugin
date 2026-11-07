"""
10041 排查：把 v2 命名的 Cookie 字段映射成旧字段名（ltoken / ltuid / cookie_token）再试。
部分 record 接口只认旧字段名。
"""
import sqlite3
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.api.ds_sign import SALT_4X, generate_ds2  # noqa: E402

DB = Path(r"C:\Users\admin\.dsh\dsh-roost\roost\plugins\dsh-starrail\data\starrail.db")
NOTE = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"
INDEX = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/index"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def call(url, params, cookie):
    headers = {
        "Cookie": cookie,
        "DS": generate_ds2(params=params, body=None, salt=SALT_4X),
        "x-rpc-app_version": "2.63.1",
        "x-rpc-client_type": "5",
        "x-rpc-device_id": "5f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
        "x-rpc-language": "zh-cn",
        "Referer": "https://webstatic.mihoyo.com/",
        "User-Agent": UA,
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    d = r.json()
    return d.get("retcode"), (str(d.get("message") or d.get("msg") or ""))[:40]


def main():
    con = sqlite3.connect(DB)
    cookie, uid, region = con.execute("SELECT cookie, uid, region FROM user_bind LIMIT 1").fetchone()
    con.close()
    p = {"role_id": uid, "server": region}

    pairs = {}
    for kv in cookie.split(";"):
        kv = kv.strip()
        if "=" in kv:
            k, v = kv.split("=", 1)
            pairs[k] = v

    ltuid = pairs.get("ltuid_v2", "")
    ltoken = pairs.get("ltoken_v2", "")
    ctoken = pairs.get("cookie_token_v2", "")
    mid = pairs.get("account_id", "")

    variants = [
        ("原样", cookie),
        ("+ltoken+ltuid", cookie + f"; ltoken={ltoken}; ltuid={ltuid}; stuid={ltuid}; stoken={ltoken}"),
        ("+cookie_token", cookie + f"; cookie_token={ctoken}"),
        ("+mid+ltoken+ltuid+cookie_token",
         cookie + f"; mid={mid}; ltoken={ltoken}; ltuid={ltuid}; stoken={ltoken}; cookie_token={ctoken}"),
        ("全旧字段", f"ltoken={ltoken}; ltuid={ltuid}; stoken={ltoken}; cookie_token={ctoken}; mid={mid}"),
    ]
    for name, ck in variants:
        for url, tag in ((NOTE, "note"), (INDEX, "index")):
            try:
                code, msg = call(url, p, ck)
            except Exception as e:
                code, msg = "EXC", str(e)[:30]
            print(f"  {name:28s} {tag:6s} -> retcode={code} message={msg}")


if __name__ == "__main__":
    main()
