"""
米游社扫码登录
规范：https://uigf.org/zh/mihoyo-api-collection/hoyolab/login/qrcode_hoyolab.html

与其它接口不同，这两个端点不需要 Cookie，也不需要 DS 签名，
只要 x-rpc-app_id、x-rpc-device_id 和标准请求头。

流程：
1. createQRLogin → 拿到 url（二维码内容）与 ticket
2. 用户用米游社 App 扫码并确认
3. queryQRLoginStatus 轮询，确认后从 **响应头 Set-Cookie** 取账号凭证
"""
import uuid
from typing import Optional
from urllib.parse import quote

import requests

from .config import (
    QR_APP_ID, QR_IMAGE_API, QR_RETCODE_CANCELLED, QR_RETCODE_EXPIRED,
    QR_REFERER, QR_STATUS_CONFIRMED, REQUEST_TIMEOUT, URL_QR_CREATE, URL_QR_QUERY,
)
from ..utils.logger import Logger

logger = Logger("QrLogin")


class QrLoginError(Exception):
    def __init__(self, retcode: int, message: str):
        self.retcode = retcode
        self.message = message
        super().__init__(f"[{retcode}] {message}")


def new_device_id() -> str:
    return str(uuid.uuid4()).upper()


def _headers(device_id: str) -> dict:
    return {
        "Host": "passport-api.miyoushe.com",
        "Origin": "https://user.mihoyo.com",
        "Referer": QR_REFERER,
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13; M2101K9C Build/TKQ1.220829.002; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/108.0.5359.128 "
            "Mobile Safari/537.36 miHoYoBBS/2.71.1"
        ),
        "x-rpc-app_id": QR_APP_ID,
        "x-rpc-device_id": device_id,
        "Content-Type": "application/json",
    }


def create_qr(device_id: Optional[str] = None) -> tuple[str, str]:
    """返回 (二维码指向的登录链接, ticket)"""
    device_id = device_id or new_device_id()
    try:
        resp = requests.post(URL_QR_CREATE, headers=_headers(device_id), json={},
                             timeout=REQUEST_TIMEOUT)
        body = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("创建二维码失败", e)
        raise QrLoginError(-1, "无法连接米游社，请稍后重试")

    if body.get("retcode") != 0:
        raise QrLoginError(body.get("retcode", -1), body.get("message", "未知错误"))

    data = body.get("data") or {}
    url, ticket = data.get("url"), data.get("ticket")
    if not url or not ticket:
        raise QrLoginError(-1, "米游社未返回二维码信息")

    logger.info(f"二维码已创建 ticket={ticket[:8]}...")
    return url, ticket


def qr_image_url(login_url: str) -> Optional[str]:
    """
    把登录链接交给公网二维码服务渲染成图片地址。
    roost 的 reply_image 只吃远程 URL，本地生成的 PNG 发不出去。
    """
    if not QR_IMAGE_API:
        return None
    return QR_IMAGE_API.format(data=quote(login_url, safe=""))


def _parse_set_cookie(headers) -> dict:
    """从响应头里抽出所有 Set-Cookie 的键值"""
    cookies = {}
    for raw in headers.get_all("Set-Cookie", []) or []:
        pair = raw.split(";")[0]
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        cookies[k.strip()] = v.strip()
    return cookies


def query_qr(ticket: str, device_id: str) -> tuple[str, dict]:
    """
    查询扫码状态。
    返回 (status, cookie)；只有 Confirmed 时 cookie 才有值。
    status: Created / Scanned / Confirmed
    """
    try:
        resp = requests.post(URL_QR_QUERY, headers=_headers(device_id),
                             json={"ticket": ticket}, timeout=REQUEST_TIMEOUT)
        body = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("查询扫码状态失败", e)
        raise QrLoginError(-1, "无法连接米游社，请稍后重试")

    retcode = body.get("retcode", -1)
    if retcode == QR_RETCODE_EXPIRED:
        raise QrLoginError(retcode, "二维码已过期，请重新发送 #星铁扫码登录")
    if retcode == QR_RETCODE_CANCELLED:
        raise QrLoginError(retcode, "已在手机上取消登录")
    if retcode != 0:
        raise QrLoginError(retcode, body.get("message", "未知错误"))

    data = body.get("data") or {}
    status = data.get("status", "")

    if status != QR_STATUS_CONFIRMED:
        return status, {}

    cookies = _parse_set_cookie(resp.headers)
    if not cookies:
        logger.warn("确认登录但响应头没有 Set-Cookie")
        raise QrLoginError(-1, "登录已确认，但没拿到账号凭证，请重试")

    logger.info(f"扫码确认成功，拿到 {len(cookies)} 个 Cookie 字段")
    return status, cookies


def build_cookie_string(cookies: dict) -> str:
    """
    拼成接口可用的 Cookie 串。
    ltoken_v2 必须与 ltmid_v2 一起使用（UIGF 鉴权文档）。
    只保留确认拿到的字段，不要凭空补值。
    """
    parts = []
    for key in ("ltoken_v2", "ltmid_v2", "ltuid_v2", "account_id", "account_id_v2",
                "cookie_token_v2", "cookie_token", "login_uid", "mid"):
        value = cookies.get(key)
        if value:
            parts.append(f"{key}={value}")

    if "ltoken_v2" in cookies and "ltmid_v2" not in cookies:
        raise QrLoginError(-1, "缺少 ltmid_v2，无法拼出可用 Cookie")

    return "; ".join(parts)


def has_required(cookies: dict) -> bool:
    return all(cookies.get(k) for k in ("ltoken_v2", "ltmid_v2"))
