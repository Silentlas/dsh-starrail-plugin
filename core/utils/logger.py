"""
日志工具
所有输出一律走 stderr：stdout 是 roost 的协议通道，写入任何非 JSON 内容都会破坏协议
敏感信息（Cookie / authkey / token）自动脱敏
"""
import os
import re
import sys
from datetime import datetime

_SENSITIVE_PATTERNS = [
    (re.compile(r"((?:cookie|authkey|token|stoken|ltoken|ltuid)\s*[=:]\s*)([^;,\s]+)", re.I), r"\1***"),
]


def mask(text: str) -> str:
    """脱敏敏感字段"""
    result = str(text)
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class Logger:
    def __init__(self, prefix: str):
        self.prefix = f"[{prefix}]"

    def _emit(self, level: str, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sys.stderr.write(f"{ts} {self.prefix} [{level}] {mask(message)}\n")
        sys.stderr.flush()

    def info(self, message: str) -> None:
        self._emit("INFO", message)

    def warn(self, message: str) -> None:
        self._emit("WARN", message)

    def error(self, message: str, error: Exception = None) -> None:
        suffix = f" | error: {error}" if error else ""
        self._emit("ERROR", f"{message}{suffix}")

    def debug(self, message: str) -> None:
        if os.getenv("DEBUG"):
            self._emit("DEBUG", message)
