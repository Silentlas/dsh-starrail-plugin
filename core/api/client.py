"""
米游社API客户端
基础请求封装，DS签名、错误处理
"""
import time
import requests
from typing import Optional

from .config import DEFAULT_HEADERS, REQUEST_INTERVAL
from .ds_sign import generate_ds, generate_device_id
from ..utils.logger import Logger

logger = Logger("MhyApi")


class MhyApiError(Exception):
    def __init__(self, retcode: int, message: str):
        self.retcode = retcode
        self.message = message
        super().__init__(f"[{retcode}] {message}")


class MhyClient:
    def __init__(self, cookie: str):
        self.cookie = cookie
        self.session = requests.Session()
        self.last_request_time = 0
        self.device_id = generate_device_id()

    def _get_headers(self, params: Optional[dict] = None, body: Optional[dict] = None) -> dict:
        headers = DEFAULT_HEADERS.copy()
        headers["Cookie"] = self.cookie
        headers["x-rpc-device_id"] = self.device_id
        # 生成DS签名
        headers["DS"] = generate_ds(query=params, body=body)
        return headers

    def _need_wait(self) -> float:
        """计算需要等待的时间，避免请求过快"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < REQUEST_INTERVAL:
            return REQUEST_INTERVAL - elapsed
        return 0

    def request(self, method: str, url: str, params: Optional[dict] = None,
                data: Optional[dict] = None, json: Optional[dict] = None) -> dict:
        """统一请求方法，自动处理频率、签名、错误"""
        wait = self._need_wait()
        if wait > 0:
            time.sleep(wait)

        headers = self._get_headers(params=params, body=json)

        try:
            resp = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                timeout=10
            )
            self.last_request_time = time.time()
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as e:
            logger.error("请求失败", e)
            raise MhyApiError(-1, "网络请求失败，请稍后重试")

        retcode = result.get("retcode", -1)
        message = result.get("message", "未知错误")

        if retcode != 0:
            logger.warn(f"API返回错误: [{retcode}] {message}")
            # 常见错误码处理
            if retcode in [-100, 10001]:
                raise MhyApiError(retcode, "Cookie已失效，请重新绑定")
            raise MhyApiError(retcode, message)

        return result.get("data", {})

    def get(self, url: str, params: Optional[dict] = None) -> dict:
        return self.request("GET", url, params=params)

    def post(self, url: str, data: Optional[dict] = None, json: Optional[dict] = None) -> dict:
        return self.request("POST", url, data=data, json=json)
