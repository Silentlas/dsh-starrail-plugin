"""
游戏登录二维码（combo/panda）流程
与扫码网页登录的区别：
- 这里扫的是「登录游戏」的二维码，扫完拿到的是 game_token
- game_token 可以换到 stoken，再换出 ltoken / cookie_token（v1 凭证）
- v1 凭证才是战绩类接口（note/index/角色练度）认的，网页扫码给的 ltoken_v2 权限不够

契约：
1. fetch 与 query 必须用同一个 device（就是 body 里的 device 字段）
2. ticket 在 data 里可能为 null，得从 url 尾部截 24 位
3. 查询返回 Confirmed 时，data.payload.raw 是 JSON 字符串，含 uid 与 token
"""
import json
import uuid
from urllib.parse import quote

import requests

from .config import (
    GAME_QR_APP_ID, URL_GAME_QR_FETCH, URL_GAME_QR_QUERY,
    URL_S_TOKEN_BY_GAME_TOKEN, URL_LTOKEN_BY_STOKEN, URL_COOKIE_BY_STOKEN,
    URL_STOKEN_V2_BY_V1, REQUEST_TIMEOUT,
)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 miHoYoBBS/2.76.1")

GAME_QR_STATUS_WAIT = "Init"
GAME_QR_STATUS_SCANNED = "Scanned"
GAME_QR_STATUS_CONFIRMED = "Confirmed"
GAME_QR_STATUS_CANCELLED = "Cancelled"
GAME_QR_STATUS_EXPIRED = "Expired"


class GameQrError(Exception):
    def __init__(self, retcode, message):
        self.retcode = retcode
        self.message = message
        super().__init__(f"[{retcode}] {message}")


def new_device_id() -> str:
    return str(uuid.uuid4()).upper()


def _post(url: str, body: dict, headers: dict | None = None) -> dict:
    h = {"Content-Type": "application/json", "User-Agent": UA}
    if headers:
        h.update(headers)
    try:
        resp = requests.post(url, json=body, headers=h, timeout=REQUEST_TIMEOUT)
        return resp.json()
    except Exception as e:
        raise GameQrError(-1, f"请求失败：{e}")


def _get(url: str, params: dict) -> dict:
    try:
        resp = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
        return resp.json()
    except Exception as e:
        raise GameQrError(-1, f"请求失败：{e}")


def fetch_qr(device_id: str) -> tuple[str, str]:
    """取游戏登录二维码，返回 (二维码内容 url, ticket)"""
    data = _post(URL_GAME_QR_FETCH, {"app_id": GAME_QR_APP_ID, "device": device_id},
                 {"x-rpc-app_id": "bll8iq97cem8"})
    if data.get("retcode") != 0:
        raise GameQrError(data.get("retcode"), data.get("message") or "获取二维码失败")

    payload = data.get("data") or {}
    qr_url = payload.get("url")
    if not qr_url:
        raise GameQrError(-1, "接口没有返回二维码链接")
    # ticket 有时为空，从 url 尾部取 24 位
    ticket = payload.get("ticket") or qr_url[-24:]
    return qr_url, ticket


def query_status(ticket: str, device_id: str) -> tuple[str, dict]:
    """
    查询扫码状态，返回 (status, data)
    注意：接口返回的字段名是 stat（不是 status），未扫码时值是 "Init"
    """
    data = _post(URL_GAME_QR_QUERY,
                 {"app_id": GAME_QR_APP_ID, "device": device_id, "ticket": ticket},
                 {"x-rpc-app_id": "bll8iq97cem8"})
    if data.get("retcode") != 0:
        raise GameQrError(data.get("retcode"), data.get("message") or "查询扫码状态失败")
    payload = data.get("data") or {}
    status = payload.get("stat") or payload.get("status") or GAME_QR_STATUS_WAIT
    return status, payload


def parse_payload(payload: dict) -> tuple[str, str, dict]:
    """从 Confirmed 的 payload 里取出 (uid, game_token, 原始字段)"""
    raw = payload.get("raw")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as e:
            raise GameQrError(-1, f"登录凭证解析失败：{e}")
    if not isinstance(raw, dict):
        raise GameQrError(-1, "登录凭证格式异常")
    uid = str(raw.get("uid") or raw.get("account_id") or "")
    token = raw.get("token") or raw.get("game_token") or ""
    if not uid or not token:
        raise GameQrError(-1, "登录凭证缺少 uid 或 token")
    return uid, token, raw


def exchange_stoken(account_id: str, game_token: str) -> tuple[str, str]:
    """用 game_token 换 (mid, stoken)"""
    data = _post(URL_S_TOKEN_BY_GAME_TOKEN, {"account_id": int(account_id), "game_token": game_token},
                 {"x-rpc-app_id": "bll8iq97cem8", "Referer": "https://app.mihoyo.com"})
    if data.get("retcode") != 0:
        raise GameQrError(data.get("retcode"), data.get("message") or "换取 SToken 失败")
    payload = data.get("data") or {}
    mid = str((payload.get("user_info") or {}).get("mid") or "")
    stoken = ((payload.get("token") or {}).get("token") or "")
    if not stoken:
        raise GameQrError(-1, "接口没有返回 SToken")
    return mid, stoken


def stoken_to_cookie(mid: str, stoken: str) -> str:
    """
    用 SToken 换 ltoken / cookie_token，拼出 v1 版 Cookie。
    v1 凭证（ltoken + cookie_token + stoken）才是战绩类接口认的。
    """
    uid = mid or ""
    parts = []
    if mid:
        parts.append(f"mid={mid}")

    ltoken = ""
    ltoken_data = _get(URL_LTOKEN_BY_STOKEN, {"stoken": stoken, "uid": uid})
    if ltoken_data.get("retcode") == 0:
        ltoken = (ltoken_data.get("data") or {}).get("ltoken") or ""
    if not ltoken:
        raise GameQrError(ltoken_data.get("retcode", -1),
                          ltoken_data.get("message") or "用 SToken 换 ltoken 失败")

    cookie_token = ""
    ct_data = _get(URL_COOKIE_BY_STOKEN, {"stoken": stoken, "uid": uid})
    if ct_data.get("retcode") == 0:
        data = ct_data.get("data") or {}
        cookie_token = data.get("cookie_token") or (data.get("token") or {}).get("token") or ""

    parts.append(f"ltoken={ltoken}")
    parts.append(f"ltuid={uid}")
    if cookie_token:
        parts.append(f"cookie_token={cookie_token}")
    parts.append(f"stoken={stoken}")
    if uid:
        parts.append(f"account_id={uid}")

    # 顺手换一份 stoken_v2，部分新接口只认 v2
    try:
        v2 = _post(URL_STOKEN_V2_BY_V1, {"stoken": stoken, "mid": uid},
                   {"x-rpc-app_id": "bll8iq97cem8", "Referer": "https://app.mihoyo.com"})
        if v2.get("retcode") == 0:
            token = ((v2.get("data") or {}).get("token") or {}).get("token") or ""
            if token:
                parts.append(f"stoken_v2={token}")
    except GameQrError:
        pass

    return "; ".join(parts)


def qr_image_url(qr_content: str) -> str:
    """把二维码内容渲染成公网图片（roost 只能发远程图片）"""
    from .config import QR_IMAGE_API
    return QR_IMAGE_API.format(data=quote(qr_content, safe=""))
