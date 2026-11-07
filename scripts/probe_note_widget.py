"""
10041 根因排查：note 端点可能要求 SToken/完整 Cookie，
社区实现（nonebot-plugin-mystool）走的是 widget 端点：
  https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/aapi/widget
本脚本对比 note / widget 两种端点在各 Cookie 组合下的结果。
"""
import sqlite3
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.api.ds_sign import SALT_4X, generate_ds1, generate_ds2, SALT_K2  # noqa: E402

DB = Path(r"C:\Users\admin\.dsh\dsh-roost\roost\data\bots\main\plugins\dsh-starrail\starrail.db")
NOTE = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"
WIDGET = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/aapi/widget"

UA_APP = ("Mozilla/5.0 (Linux; Android 12; Mi 10) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 miHoYoBBS/2.63.1")
UA_WIDGET = ("Mozilla/5.0 (Linux; Android 12; Mi 10) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36 miHoYoBBS/2.63.1")


def load_cookie():
    con = sqlite3.connect(DB)
    cookie = con.execute("SELECT cookie FROM user_bind LIMIT 1").fetchone()[0]
    con.close()
    return cookie


def pairs_of(cookie):
    d = {}
    for kv in cookie.split(";"):
        kv = kv.strip()
        if "=" in kv:
            k, v = kv.split("=", 1)
            d[k] = v
    return d


def get(url, params, cookie, headers):
    h = dict(headers)
    h["Cookie"] = cookie
    try:
        r = requests.get(url, params=params, headers=h, timeout=15)
        d = r.json()
        return d.get("retcode"), (str(d.get("message") or d.get("msg") or ""))[:40], d.get("data")
    except Exception as e:
        return "EXC", str(e)[:40], None


def main():
    cookie = load_cookie()
    p = pairs_of(cookie)
    ltuid = p.get("ltuid_v2", "")
    ck_full = cookie + f"; ltuid={ltuid}; stuid={ltuid}; account_mid_v2={p.get('account_mid_v2','')}"

    widget_headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "User-Agent": UA_WIDGET,
        "Referer": "https://app.mihoyo.com",
        "x-rpc-app_version": "2.63.1",
        "x-rpc-channel": "appstore",
        "x-rpc-client_type": "2",
        "x-rpc-device_fp": "",
        "x-rpc-device_id": "",
        "x-rpc-device_model": "Mi 10",
        "x-rpc-device_name": "Mi 10",
        "x-rpc-sys_version": "12",
    }

    print("== widget 端点（client_type=2 + DS1）==")
    for label, ck in (("6 字段", cookie), ("补 ltuid/account_mid_v2", ck_full)):
        code, msg, data = get(WIDGET, {}, ck, dict(widget_headers, DS=generate_ds1(SALT_K2)))
        brief = "" if not data else f" stamina={data.get('current_stamina')}/{data.get('max_stamina')}"
        print(f"  {label:22s} -> retcode={code} message={msg}{brief}")

    print("\n== widget + client_type=5 + DS2 ==")
    for ds_label, ds in (("DS2(空)", generate_ds2()),
                         ("无 DS", "")):
        h = dict(widget_headers)
        h["x-rpc-client_type"] = "5"
        if ds:
            h["DS"] = ds
        code, msg, data = get(WIDGET, {}, cookie, h)
        brief = "" if not data else f" stamina={data.get('current_stamina')}/{data.get('max_stamina')}"
        print(f"  {ds_label:22s} -> retcode={code} message={msg}{brief}")

    print("\n== note 端点补 ltuid/account_mid_v2（client_type=5）==")
    h = {
        "Cookie": ck_full,
        "DS": generate_ds2(params={"role_id": p.get("ui", ""), "server": "prod_gf_cn"}, salt=SALT_4X),
        "x-rpc-app_version": "2.63.1",
        "x-rpc-client_type": "5",
        "x-rpc-device_id": "5f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
        "Referer": "https://webstatic.mihoyo.com/",
        "User-Agent": UA_APP,
    }
    con = sqlite3.connect(DB)
    uid, region = con.execute("SELECT uid, region FROM user_bind LIMIT 1").fetchone()
    con.close()
    h["DS"] = generate_ds2(params={"role_id": uid, "server": region}, salt=SALT_4X)
    code, msg, data = get(NOTE, {"role_id": uid, "server": region}, ck_full, h)
    print(f"  note 全字段 -> retcode={code} message={msg}")


if __name__ == "__main__":
    main()
