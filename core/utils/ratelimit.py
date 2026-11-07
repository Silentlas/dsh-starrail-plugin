"""
频率限制工具
单用户每分钟2次，全群每分钟10次
"""
import time
from .logger import Logger

logger = Logger("RateLimit")


class Bucket:
    def __init__(self, tokens: float, last_refill: float):
        self.tokens = tokens
        self.last_refill = last_refill


class RateLimiter:
    def __init__(self):
        self.user_buckets: dict[str, Bucket] = {}
        self.group_buckets: dict[str, Bucket] = {}
        self.user_limit = 2  # 每分钟2次
        self.group_limit = 10  # 每分钟10次
        self.window_ms = 60 * 1000  # 1分钟窗口

    def _refill(self, bucket: Bucket, limit: int):
        now = time.time() * 1000
        elapsed = now - bucket.last_refill
        refill_tokens = (elapsed / self.window_ms) * limit
        bucket.tokens = min(limit, bucket.tokens + refill_tokens)
        bucket.last_refill = now

    def check_user(self, qq_id: str) -> bool:
        bucket = self.user_buckets.get(qq_id)
        if not bucket:
            bucket = Bucket(tokens=self.user_limit, last_refill=time.time() * 1000)
            self.user_buckets[qq_id] = bucket
        self._refill(bucket, self.user_limit)
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True
        logger.warn(f"用户 {qq_id} 触发频率限制")
        return False

    def check_group(self, group_id: str) -> bool:
        bucket = self.group_buckets.get(group_id)
        if not bucket:
            bucket = Bucket(tokens=self.group_limit, last_refill=time.time() * 1000)
            self.group_buckets[group_id] = bucket
        self._refill(bucket, self.group_limit)
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True
        logger.warn(f"群 {group_id} 触发频率限制")
        return False


rate_limiter = RateLimiter()
