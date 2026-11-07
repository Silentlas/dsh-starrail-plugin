"""
继续定位 10041：测参数形态（role_id 类型 / 缺省参数 / 错误参数）。
如果一个「明显错误的参数」也返回 10041，说明校验来自账号状态而不是参数。
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
INDEX = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/index"
NOTE = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"
ROLES = "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie"
BBS = "https://bbs-api.miyoushe.com/user/api/getUserFullInfo"


def call(url, params, cookie):
    headers = {
        "Cookie": cookie,
        "DS": generate_ds2(params=params, body=None, salt=SALT_4X),
        "x-rpc-app_version": "2.63.1",
        "x-rpc-client_type": "5",
        "x-rpc-device_id": "5f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
        "x-rpc-language": "zh-cn",
        "Referer": "https://webstatic.mihoyo.com/",
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    d = r.json()
    return d.get("retcode"), (str(d.get("message") or d.get("msg") or ""))[:50]


def main():
    con = sqlite3.connect(DB)
    cookie, uid, region = con.execute("SELECT cookie, uid, region FROM user_bind LIMIT 1").fetchone()
    con.close()
    print(f"uid={uid} region={region}")

    cases = [
        ("index role_id=str", INDEX, {"role_id": uid, "server": region}),
        ("index role_id=int", INDEX, {"role_id": int(uid), "server": region}),
        ("index 无 role_id", INDEX, {"server": region}),
        ("index 假 uid", INDEX, {"role_id": "100000001", "server": region}),
        ("note role_id=int", NOTE, {"role_id": int(uid), "server": region}),
        ("note 假 uid", NOTE, {"role_id": "100000001", "server": region}),
        ("roles(对照，应 0)", ROLES, {"game_biz": "hkrpg_cn"}),
        ("bbs getUserFullInfo", BBS, {}),
    ]
    for name, url, params in cases:
        try:
            code, msg = call(url, params, cookie)
        except Exception as e:
            code, msg = "EXC", str(e)[:40]
        print(f"  {name:22s} -> retcode={code} message={msg}")


if __name__ == "__main__":
    main()
