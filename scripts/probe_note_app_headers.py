"""
照抄 qq-boot（星铁 QQ 机器人）的完整 App 头再打一次 note：
x-rpc-client_type=5 + DS2，同时带 device_fp / verify_key / channel=sr / okhttp UA / sys_version。
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


def main():
    con = sqlite3.connect(DB)
    cookie, uid, region, dev = con.execute(
        "SELECT cookie, uid, region, device_id FROM user_bind LIMIT 1").fetchone()
    con.close()
    param = f"role_id={uid}&server={region}"

    base = {
        "x-rpc-client_type": "5",
        "x-rpc-app_version": "2.71.1",
        "x-rpc-sys_version": "9",
        "x-rpc-channel": "sr",
        "x-rpc-device_id": dev,
        "x-rpc-device_fp": "38d7fb149f617",
        "x-rpc-h265_supported": "1",
        "x-rpc-verify_key": "bll8iq97cem8",
        "accept-encoding": "gzip",
        "user-agent": "okhttp/4.9.3",
        "referer": "https://app.mihoyo.com",
        "host": "api-takumi-record.mihoyo.com",
        "Cookie": cookie,
        "DS": generate_ds2(params={"role_id": uid, "server": region}),
    }
    r = requests.get(NOTE, params={"role_id": uid, "server": region}, headers=base, timeout=15)
    d = r.json()
    print(f"  note 完整App头 -> retcode={d.get('retcode')} message={str(d.get('message') or '')[:40]}")
    if d.get("data"):
        print(f"    stamina={d['data'].get('current_stamina')}/{d['data'].get('max_stamina')}")


if __name__ == "__main__":
    main()
