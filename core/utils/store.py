"""
SQLite数据存储封装
零额外依赖，使用Python内置sqlite3
"""
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .logger import Logger

logger = Logger("Store")

DB_PATH = Path(__file__).parent.parent.parent / "data" / "starrail.db"


class UserBind:
    def __init__(self, qq_id: str, cookie: Optional[str] = None, uid: Optional[str] = None,
                 auth_key: Optional[str] = None, bind_time: int = 0, last_query_time: Optional[int] = None):
        self.qq_id = qq_id
        self.cookie = cookie
        self.uid = uid
        self.auth_key = auth_key
        self.bind_time = bind_time
        self.last_query_time = last_query_time


class Store:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_bind (
                    qq_id TEXT PRIMARY KEY,
                    cookie TEXT,
                    uid TEXT,
                    auth_key TEXT,
                    bind_time INTEGER NOT NULL,
                    last_query_time INTEGER
                )
            """)
            logger.debug("数据库初始化完成")

    def get_user_bind(self, qq_id: str) -> Optional[UserBind]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_bind WHERE qq_id = ?", (qq_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return UserBind(
                qq_id=row["qq_id"],
                cookie=row["cookie"],
                uid=row["uid"],
                auth_key=row["auth_key"],
                bind_time=row["bind_time"],
                last_query_time=row["last_query_time"]
            )

    def set_user_bind(self, qq_id: str, data: dict):
        import time
        existing = self.get_user_bind(qq_id)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if existing:
                update_fields = []
                params = []
                for k, v in data.items():
                    if k in ["cookie", "uid", "auth_key", "last_query_time"]:
                        update_fields.append(f"{k} = ?")
                        params.append(v)
                params.append(qq_id)
                cursor.execute(f"UPDATE user_bind SET {', '.join(update_fields)} WHERE qq_id = ?", params)
            else:
                cursor.execute("""
                    INSERT INTO user_bind (qq_id, cookie, uid, auth_key, bind_time)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    qq_id,
                    data.get("cookie"),
                    data.get("uid"),
                    data.get("auth_key"),
                    int(time.time())
                ))
            logger.debug(f"更新用户绑定: {qq_id}")

    def remove_user_bind(self, qq_id: str):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_bind WHERE qq_id = ?", (qq_id,))
            logger.debug(f"删除用户绑定: {qq_id}")


store = Store()
