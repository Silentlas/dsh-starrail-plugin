"""用库里保存的 device_id 复现 note 请求，验证设备一致性是否就是 10041 的原因"""
import sqlite3
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.api.client import MhyClient  # noqa: E402
from core.api.record import get_note  # noqa: E402

CANDIDATE_DBS = [
    Path(r"C:\Users\admin\.dsh\dsh-roost\roost\data\bots\main\plugins\dsh-starrail\starrail.db"),
    Path(r"C:\Users\admin\.dsh\dsh-roost\roost\plugins\dsh-starrail\data\starrail.db"),
]

for db in CANDIDATE_DBS:
    if not db.exists():
        continue
    con = sqlite3.connect(db)
    cols = [r[1] for r in con.execute("PRAGMA table_info(user_bind)")]
    row = con.execute("SELECT qq_id, cookie, uid, region, nickname, device_id FROM user_bind LIMIT 1").fetchone() \
        if "device_id" in cols else None
    con.close()
    if not row:
        print(f"{db.name}: 无记录或有 device_id 列缺失（列={cols}）")
        continue
    qq, cookie, uid, region, nick, dev = row
    print(f"\n库: {db}")
    print(f"  uid={uid} region={region} nick={nick} device_id={dev}")

    for label, dev_id in (("带 device_id", dev), ("随机 device_id", None)):
        client = MhyClient(cookie, device_id=dev_id)
        try:
            data = get_note(client, uid, region)
            print(f"  {label}: 成功 current_stamina={data.get('current_stamina')}/{data.get('max_stamina')}")
        except Exception as e:
            print(f"  {label}: 失败 {e}")
