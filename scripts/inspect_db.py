"""检查两个候选数据库里的绑定记录（只打印数量与打码后的字段）"""
import sqlite3
from pathlib import Path

DBS = [
    Path(r"C:\Users\admin\.dsh\dsh-roost\roost\data\bots\main\plugins\dsh-starrail\starrail.db"),
    Path(r"D:\Personal data\星铁机器人\data\starrail.db"),
]

for db in DBS:
    print("\n==", db)
    print("   存在:", db.exists(), "大小:", db.stat().st_size if db.exists() else 0)
    if not db.exists():
        continue
    con = sqlite3.connect(db)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("   表:", tables)
    if "user_bind" in tables:
        rows = con.execute("SELECT qq_id, uid, region, nickname, length(cookie) FROM user_bind").fetchall()
        print("   user_bind 行数:", len(rows))
        for r in rows:
            print("     qq=%s... uid=%s region=%s nick=%s cookie长度=%s" % (str(r[0])[:8], r[1], r[2], r[3], r[4]))
    con.close()
