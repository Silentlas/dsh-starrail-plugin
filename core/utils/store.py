"""
SQLite 数据存储
数据库位置优先使用 roost 下发的 dataDir（按机器人隔离），
本地调试时无 dataDir 则退化为项目内 data/starrail.db
"""
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .logger import Logger

logger = Logger("Store")

_FALLBACK_DB = Path(__file__).resolve().parent.parent.parent / "data" / "starrail.db"


class UserBind:
    """用户的绑定信息"""

    def __init__(self, qq_id: str, cookie: Optional[str] = None, uid: Optional[str] = None,
                 region: Optional[str] = None, nickname: Optional[str] = None,
                 auth_key: Optional[str] = None, bind_time: int = 0,
                 last_query_time: Optional[int] = None):
        self.qq_id = qq_id
        self.cookie = cookie
        self.uid = uid
        self.region = region
        self.nickname = nickname
        self.auth_key = auth_key
        self.bind_time = bind_time
        self.last_query_time = last_query_time


class Store:
    def __init__(self, db_path: Path | str = _FALLBACK_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_bind (
                    qq_id TEXT PRIMARY KEY,
                    cookie TEXT,
                    uid TEXT,
                    region TEXT,
                    nickname TEXT,
                    auth_key TEXT,
                    bind_time INTEGER NOT NULL,
                    last_query_time INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gacha_record (
                    id TEXT PRIMARY KEY,
                    uid TEXT NOT NULL,
                    gacha_type TEXT NOT NULL,
                    item_name TEXT,
                    item_type TEXT,
                    rank_type TEXT,
                    gacha_time TEXT,
                    pulled_at INTEGER
                )
            """)
        logger.debug(f"数据库就绪: {self.db_path}")

    def get_user_bind(self, qq_id: str) -> Optional[UserBind]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM user_bind WHERE qq_id = ?", (qq_id,)).fetchone()
        if not row:
            return None
        return UserBind(
            qq_id=row["qq_id"], cookie=row["cookie"], uid=row["uid"],
            region=row["region"], nickname=row["nickname"], auth_key=row["auth_key"],
            bind_time=row["bind_time"], last_query_time=row["last_query_time"],
        )

    def set_user_bind(self, qq_id: str, data: dict):
        allowed = {"cookie", "uid", "region", "nickname", "auth_key", "last_query_time"}
        fields = [(k, v) for k, v in data.items() if k in allowed]
        with self._conn() as conn:
            if self.get_user_bind(qq_id):
                if not fields:
                    return
                assignments = ", ".join(f"{k} = ?" for k, _ in fields)
                conn.execute(
                    f"UPDATE user_bind SET {assignments} WHERE qq_id = ?",
                    [v for _, v in fields] + [qq_id],
                )
            else:
                conn.execute("""
                    INSERT INTO user_bind (qq_id, cookie, uid, region, nickname, auth_key, bind_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (qq_id, data.get("cookie"), data.get("uid"), data.get("region"),
                      data.get("nickname"), data.get("auth_key"), int(time.time())))
        logger.debug(f"更新用户绑定: {qq_id}")

    def remove_user_bind(self, qq_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM user_bind WHERE qq_id = ?", (qq_id,))
        logger.debug(f"删除用户绑定: {qq_id}")


_store: Optional[Store] = None


def init_store(data_dir: Optional[str] = None) -> Store:
    """由插件入口在收到 init 时调用，指定真正的存储位置"""
    global _store
    db_path = Path(data_dir) / "starrail.db" if data_dir else _FALLBACK_DB
    _store = Store(db_path)
    return _store


def get_store() -> Store:
    """惰性初始化，本地调试时未调用 init_store 也能用"""
    global _store
    if _store is None:
        _store = Store(_FALLBACK_DB)
    return _store
