"""
日志工具，自动脱敏敏感信息
"""
import re
import sys
from datetime import datetime


class Logger:
    def __init__(self, prefix: str):
        self.prefix = f"[{prefix}]"

    def _mask_sensitive(self, text: str) -> str:
        """脱敏Cookie、authkey、token等敏感信息"""
        patterns = [
            r'(cookie|authkey|token|stoken)\s*[=:]\s*([^\s;&]+)',
            r'((?:cookie|authkey|token|stoken)["\']?\s*[:=]\s*["\']?)([^\s"\'&]+)',
        ]
        result = text
        for pattern in patterns:
            result = re.sub(pattern, r'\1=***', result, flags=re.IGNORECASE)
        return result

    def info(self, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{ts} {self.prefix} [INFO] {self._mask_sensitive(message)}")

    def warn(self, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{ts} {self.prefix} [WARN] {self._mask_sensitive(message)}", file=sys.stderr)

    def error(self, message: str, error: Exception = None):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        err_msg = f" | error: {error}" if error else ""
        print(f"{ts} {self.prefix} [ERROR] {self._mask_sensitive(message)}{err_msg}", file=sys.stderr)

    def debug(self, message: str):
        import os
        if os.getenv("DEBUG"):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{ts} {self.prefix} [DEBUG] {self._mask_sensitive(message)}")
