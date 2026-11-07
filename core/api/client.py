"""
米游社 API 客户端
统一请求封装：DS 签名、请求头、频率控制、错误码处理
请求头规范见 UIGF-org「鉴权」文档
"""
import time
from typing import Optional
from urllib.parse import urlparse

import requests

from .config import REQUEST_TIMEOUT, REQUEST_INTERVAL
from .ds_sign import APP_VERSION, CLIENT_TYPE, generate_device_id, generate_ds
from ..utils.logger import Logger

logger = Logger("MhyApi")


class MhyApiError(Exception):
    """米游社接口异常"""

    def __init__(self, retcode: int, message: str):
        self.retcode = retcode
        self.message = message
        super().__init__(f"[{retcode}] {message}")


class MhyClient:
    """一个 Cookie 对应一个客户端实例"""

    def __init__(self, cookie: str, device_id: Optional[str] = None):
        self.cookie = cookie
        self.session = requests.Session()
        self.last_request_time = 0.0
        # 扫码登录时用的是某个 device_id，凭证与该设备绑定；
        # 每次请求都换新 device_id 会被判成「非本人设备」，record 接口直接返回 10041
        self.device_id = device_id or generate_device_id()

    def _build_headers(self, url: str, params: Optional[dict], body: Optional[dict]) -> dict:
        host = urlparse(url).netloc
        return {
            "Cookie": self.cookie,
            "DS": generate_ds(params=params, body=body, client_type=CLIENT_TYPE),
            "x-rpc-app_version": APP_VERSION,
            "x-rpc-client_type": CLIENT_TYPE,
            "x-rpc-device_id": self.device_id,
            "x-rpc-language": "zh-cn",
            "X-Requested-With": "com.mihoyo.hyperion",
            "Origin": f"https://{host}",
            "Referer": "https://webstatic.mihoyo.com",
            "Host": host,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    def _throttle(self) -> None:
        """请求间隔控制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)

    def request(self, method: str, url: str, params: Optional[dict] = None,
                body: Optional[dict] = None) -> dict:
        """发起请求，返回 data 字段"""
        self._throttle()
        headers = self._build_headers(url, params, body)
        kwargs = {"headers": headers, "params": params, "timeout": REQUEST_TIMEOUT}
        if body is not None:
            kwargs["json"] = body

        try:
            resp = self.session.request(method, url, **kwargs)
            self.last_request_time = time.time()
            result = resp.json()
        except (requests.RequestException, ValueError) as e:
            logger.error("请求失败", e)
            raise MhyApiError(-1, "网络请求失败，请稍后重试")

        retcode = result.get("retcode", -1)
        message = result.get("message", "未知错误")

        if retcode != 0:
            logger.warn(f"接口返回错误: url={url} retcode={retcode} message={message}")
            raise MhyApiError(retcode, self._friendly_message(retcode, message))

        return result.get("data", {}) or {}

    @staticmethod
    def _friendly_message(retcode: int, message: str) -> str:
        """常见错误码转成用户能看懂的提示"""
        mapping = {
            -100: "Cookie 中的 login_token 无效，请重新获取",
            10001: "登录态已失效，请重新绑定 Cookie",
            10101: "账号已注销或不存在",
            10102: "账号数据未公开，请到米游社-战绩页开启「公开战绩」",
            10103: "该游戏账号未绑定此米游社账号",
            1034: "触发米游社风控验证，请稍后重试",
            -110: "请求过于频繁，请稍后再试",
            10041: "米游社拒绝了这次查询（多为账号战绩未公开，或凭证与设备不匹配）",
        }
        return mapping.get(retcode, message or f"米游社返回错误码 {retcode}")

    def get(self, url: str, params: Optional[dict] = None) -> dict:
        return self.request("GET", url, params=params)

    def post(self, url: str, body: Optional[dict] = None) -> dict:
        return self.request("POST", url, body=body)
