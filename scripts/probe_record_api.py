"""
诊断脚本：用已绑定的真实 Cookie 试探星铁 record 系列接口，
判断 note 报 10041 是端点问题、签名问题还是参数问题。
不打印 Cookie 内容。
"""
import sqlite3
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB = Path(r"C:\Users\admin\.dsh\dsh-roost\roost\plugins\dsh-starrail\data\starrail.db")

IDX = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/index"
NOTE = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"


def load_bind():
    con = sqlite3.connect(DB)
    cur = con.execute("SELECT qq_id, cookie, uid, region, nickname FROM user_bind LIMIT 1")
    row = cur.fetchone()
    con.close()
    return row


def call(url, params, cookie, client_type, app_version, extra=None):
    from core.api.ds_sign import SALT_4X, generate_ds2

    headers = {
        "Cookie": cookie,
        "DS": generate_ds2(params=params, body=None, salt=SALT_4X),
        "x-rpc-app_version": app_version,
        "x-rpc-client_type": str(client_type),
        "x-rpc-device_id": "5f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
        "x-rpc-language": "zh-cn",
        "Origin": "https://api-takumi-record.mihoyo.com",
        "Referer": "https://webstatic.mihoyo.com/",
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    }
    if extra:
        headers.update(extra)
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        data = r.json()
        return data.get("retcode"), (data.get("message") or data.get("msg") or "")[:60]
    except Exception as e:
        return "EXC", str(e)[:60]


def main():
    row = load_bind()
    if not row:
        raise SystemExit("库里没有绑定记录")
    user, cookie, uid, region, nick = row
    print(f"绑定：uid={uid} region={region} nick={nick} cookie长度={len(cookie)}")
    print(f"cookie 字段：{[kv.split('=')[0] for kv in cookie.split(';')]}")

    p_index = {"role_id": uid, "server": region}
    p_note = {"role_id": uid, "server": region}

    cases = [
        ("index  ct5 v2.63.1", IDX, p_index, 5, "2.63.1"),
        ("index  ct4 v2.63.1", IDX, p_index, 4, "2.63.1"),
        ("index  ct2 v2.63.1", IDX, p_index, 2, "2.63.1"),
        ("note   ct5 v2.63.1", NOTE, p_note, 5, "2.63.1"),
        ("note   ct4 v2.63.1", NOTE, p_note, 4, "2.63.1"),
        ("note   ct2 v2.63.1", NOTE, p_note, 2, "2.63.1"),
    ]
    for name, url, params, ct, ver in cases:
        code, msg = call(url, params, cookie, ct, ver)
        print(f"{name:22s} -> retcode={code} message={msg}")


if __name__ == "__main__":
    main()
