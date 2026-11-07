"""
诊断脚本：note/index 全部返回 10041，逐个变量试错找出缺什么。
变量：Referer / csm_source / 设备头 / app_version / Cookie 里补 mid_stuid
不打印 Cookie。
"""
import json
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
INDEX = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/index"
NOTE = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def load():
    con = sqlite3.connect(DB)
    row = con.execute("SELECT cookie, uid, region FROM user_bind LIMIT 1").fetchone()
    con.close()
    return row


def cookie_pairs(cookie):
    d = {}
    for kv in cookie.split(";"):
        kv = kv.strip()
        if "=" in kv:
            k, v = kv.split("=", 1)
            d[k] = v
    return d


def request(url, params, cookie, headers):
    headers = dict(headers)
    headers["Cookie"] = cookie
    headers["DS"] = generate_ds2(params=params, body=None, salt=SALT_4X)
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        d = r.json()
        return d.get("retcode"), (str(d.get("message") or d.get("msg") or ""))[:40]
    except Exception as e:
        return "EXC", str(e)[:40]


def base_headers(ct="5", ver="2.63.1", ref="https://webstatic.mihoyo.com/"):
    return {
        "x-rpc-app_version": ver,
        "x-rpc-client_type": ct,
        "x-rpc-device_id": "5f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
        "x-rpc-language": "zh-cn",
        "Referer": ref,
        "User-Agent": UA,
    }


def main():
    cookie, uid, region = load()
    pairs = cookie_pairs(cookie)
    print("cookie 字段:", list(pairs))
    params = {"role_id": uid, "server": region}

    print("\n== 请求头变量（note）==")
    variants = [
        ("原始", base_headers()),
        ("Referer=records页", base_headers(ref="https://webstatic.mihoyo.com/app/community-game-records/index.html?v=6")),
        ("+csm_source", dict(base_headers(), **{"x-rpc-csm_source": "community"})),
        ("+sys/channel/model", dict(base_headers(), **{
            "x-rpc-sys_version": "12", "x-rpc-channel": "miyousheluodi",
            "x-rpc-device_model": "Mi 10", "x-rpc-device_name": "Mi 10",
        })),
        ("ver=2.11.1", base_headers(ver="2.11.1")),
        ("ver=1.5.0", base_headers(ver="1.5.0")),
    ]
    for name, h in variants:
        code, msg = request(NOTE, params, cookie, h)
        print(f"  {name:16s} -> retcode={code} message={msg}")

    print("\n== Cookie 变量（note，用原始头）==")
    cvars = [
        ("原样", cookie),
        ("+mid", cookie + f"; mid={pairs.get('account_id', '')}"),
        ("+stuid", cookie + f"; stuid={pairs.get('account_id', '')}"),
        ("+mid+stuid", cookie + f"; mid={pairs.get('account_id', '')}; stuid={pairs.get('account_id', '')}"),
        ("只留 ltoken_v2+ltmid_v2", f"ltoken_v2={pairs.get('ltoken_v2','')}; ltmid_v2={pairs.get('ltmid_v2','')}"),
    ]
    for name, ck in cvars:
        code, msg = request(NOTE, params, ck, base_headers())
        print(f"  {name:22s} -> retcode={code} message={msg}")

    print("\n== index 复核（原始头）==")
    code, msg = request(INDEX, params, cookie, base_headers())
    print(f"  index -> retcode={code} message={msg}")


if __name__ == "__main__":
    main()
