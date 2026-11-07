"""
扫码登录会话管理（拉取式）
roost 插件处理完消息后上下文立刻释放，无法事后主动推送，
所以扫码不靠后台线程，而是让用户发 #星铁扫码状态 来查询。

两种模式：
- game：扫「登录游戏」的二维码（combo/panda），换到 stoken + v1 凭证，战绩类接口认这套
- web ：扫米游社网页登录二维码（passport-api），只拿到 v2 凭证，权限较低
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from ..api import game_qr
from ..api.qr_login import (
    QrLoginError, build_cookie_string, create_qr, new_device_id, qr_image_url, query_qr,
)
from ..api.config import (
    QR_POLL_INTERVAL, QR_RETCODE_CANCELLED, QR_RETCODE_EXPIRED,
    QR_STATUS_CONFIRMED, QR_STATUS_SCANNED, QR_TTL,
)
from ..utils.logger import Logger
from .service import bind_service

logger = Logger("QrService")

MODE_GAME = "game"
MODE_WEB = "web"


@dataclass
class QrSession:
    user_id: str
    mode: str
    ticket: str
    device_id: str
    login_url: str
    image_url: Optional[str]
    created_at: float = field(default_factory=time.time)
    last_poll_at: float = 0.0
    status: str = "Init"

    def expired(self) -> bool:
        return time.time() - self.created_at > QR_TTL


class QrService:
    def __init__(self):
        self._sessions: dict[str, QrSession] = {}

    # ---------- 发起 ----------
    def start(self, user_id: str, mode: str = MODE_GAME) -> tuple[bool, str, Optional[QrSession]]:
        """创建二维码会话"""
        if mode == MODE_GAME:
            return self._start_game(user_id)
        return self._start_web(user_id)

    def _start_game(self, user_id: str) -> tuple[bool, str, Optional[QrSession]]:
        device_id = game_qr.new_device_id()
        try:
            qr_content, ticket = game_qr.fetch_qr(device_id)
        except game_qr.GameQrError as e:
            return False, f"获取二维码失败：{e.message}", None

        session = QrSession(
            user_id=user_id, mode=MODE_GAME, ticket=ticket, device_id=device_id,
            login_url=qr_content, image_url=game_qr.qr_image_url(qr_content),
        )
        self._sessions[user_id] = session
        logger.info(f"用户 {user_id} 发起游戏扫码登录")

        text = (
            "请用【米游社 App】扫码，并在手机上点「确认登录」：\n"
            "「我的」→ 右上角扫码 → 相册 → 选刚保存的二维码图片\n"
            f"有效期约 {QR_TTL // 60} 分钟，扫完发送 #星铁扫码状态 完成绑定"
        )
        return True, text, session

    def _start_web(self, user_id: str) -> tuple[bool, str, Optional[QrSession]]:
        device_id = new_device_id()
        try:
            login_url, ticket = create_qr(device_id)
        except QrLoginError as e:
            return False, f"获取二维码失败：{e.message}", None

        session = QrSession(
            user_id=user_id, mode=MODE_WEB, ticket=ticket, device_id=device_id,
            login_url=login_url, image_url=qr_image_url(login_url),
        )
        self._sessions[user_id] = session
        logger.info(f"用户 {user_id} 发起网页扫码登录")

        text = (
            "请用【米游社 App】扫码并在手机上确认登录：\n"
            "「我的」→ 右上角扫码 → 相册 → 选刚保存的二维码图片\n"
            f"有效期约 {QR_TTL // 60} 分钟，扫完发送 #星铁扫码状态 完成绑定"
        )
        return True, text, session

    # ---------- 查询 ----------
    def check(self, user_id: str) -> tuple[bool, str]:
        """查询一次扫码状态；确认后直接完成绑定"""
        session = self._sessions.get(user_id)
        if not session:
            return False, "没有进行中的扫码，请先发送 #星铁扫码登录"

        if session.expired():
            self._sessions.pop(user_id, None)
            return False, "二维码已过期，请重新发送 #星铁扫码登录"

        elapsed = time.time() - session.last_poll_at
        if session.last_poll_at and elapsed < QR_POLL_INTERVAL:
            return False, "查询太频繁，请几秒后再试"
        session.last_poll_at = time.time()

        if session.mode == MODE_GAME:
            return self._check_game(session)
        return self._check_web(session)

    def _check_game(self, session: QrSession) -> tuple[bool, str]:
        try:
            status, payload = game_qr.query_status(session.ticket, session.device_id)
        except game_qr.GameQrError as e:
            logger.warn(f"用户 {session.user_id} 查询游戏扫码状态失败: [{e.retcode}] {e.message}")
            if e.retcode in (-105, -106, -3501, -3505):
                self._sessions.pop(session.user_id, None)
                return False, f"{e.message}\n二维码已失效，请重新发送 #星铁扫码登录"
            return False, e.message
        logger.info(f"游戏扫码状态: {status}")

        session.status = status

        if status == game_qr.GAME_QR_STATUS_CANCELLED:
            self._sessions.pop(session.user_id, None)
            return False, "已在手机上取消登录，请重新发送 #星铁扫码登录"
        if status == game_qr.GAME_QR_STATUS_EXPIRED:
            self._sessions.pop(session.user_id, None)
            return False, "二维码已过期，请重新发送 #星铁扫码登录"
        if status == game_qr.GAME_QR_STATUS_SCANNED:
            return True, "已扫码，请在手机上点击「确认登录」"
        if status != game_qr.GAME_QR_STATUS_CONFIRMED:
            return True, "还没有扫码，请用米游社 App 扫描二维码"

        # 已确认：game_token → stoken → v1 Cookie → 绑定
        try:
            uid, game_token, raw = game_qr.parse_payload(payload)
            mid, stoken = None, None
            # account_id 一般是游戏 uid；个别账号要传米游社 mid，失败就换候选再试一次
            candidates = [uid] + [str(raw[k]) for k in ("mid", "account_id", "account_id_v2")
                                  if raw.get(k) and str(raw[k]) != uid]
            last_err = None
            for account_id in candidates:
                try:
                    mid, stoken = game_qr.exchange_stoken(account_id, game_token)
                    break
                except game_qr.GameQrError as e:
                    last_err = e
            if not stoken:
                raise last_err or game_qr.GameQrError(-1, "换取 SToken 失败")
            cookie = game_qr.stoken_to_cookie(mid, stoken)
        except game_qr.GameQrError as e:
            logger.warn(f"用户 {session.user_id} 换取凭证失败: {e.message}")
            return False, f"换取登录凭证失败：{e.message}"

        logger.info(f"游戏扫码换取凭证成功，uid={uid} mid={mid} 字段={sorted(kv.split('=')[0] for kv in cookie.split('; '))}")
        self._sessions.pop(session.user_id, None)
        ok, msg = bind_service.bind_cookie(session.user_id, cookie, device_id=session.device_id)
        if ok:
            logger.info(f"用户 {session.user_id} 游戏扫码登录并绑定成功")
            return True, "扫码登录成功！\n\n" + msg
        return False, msg

    def _check_web(self, session: QrSession) -> tuple[bool, str]:
        try:
            status, cookies = query_qr(session.ticket, session.device_id)
        except QrLoginError as e:
            if e.retcode in (QR_RETCODE_EXPIRED, QR_RETCODE_CANCELLED):
                self._sessions.pop(session.user_id, None)
            logger.warn(f"用户 {session.user_id} 查询扫码状态失败: [{e.retcode}] {e.message}")
            return False, e.message

        session.status = status

        if status == QR_STATUS_SCANNED:
            return True, "已扫码，请在手机上点击「确认登录」"
        if status != QR_STATUS_CONFIRMED:
            return True, "还没有扫码，请用米游社 App 扫描二维码"

        logger.info(f"确认返回的 Cookie 字段: {sorted(cookies.keys())}")
        try:
            cookie = build_cookie_string(cookies)
        except QrLoginError as e:
            self._sessions.pop(session.user_id, None)
            return False, f"获取凭证失败：{e.message}"

        self._sessions.pop(session.user_id, None)
        ok, msg = bind_service.bind_cookie(session.user_id, cookie, device_id=session.device_id)
        if ok:
            logger.info(f"用户 {session.user_id} 扫码登录并绑定成功")
            return True, "扫码登录成功！\n\n" + msg
        return False, msg

    def cancel(self, user_id: str) -> tuple[bool, str]:
        if self._sessions.pop(user_id, None):
            return True, "已取消本次扫码登录"
        return False, "当前没有进行中的扫码"


qr_service = QrService()
