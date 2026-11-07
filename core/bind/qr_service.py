"""
扫码登录会话管理（拉取式）
roost 插件处理完消息后上下文立刻释放，无法事后主动推送，
所以扫码不靠后台线程，而是让用户发 #星铁扫码状态 来查询。
"""
import time
from dataclasses import dataclass, field
from typing import Optional

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


@dataclass
class QrSession:
    user_id: str
    ticket: str
    device_id: str
    login_url: str
    image_url: Optional[str]
    created_at: float = field(default_factory=time.time)
    last_poll_at: float = 0.0
    status: str = "Created"

    def expired(self) -> bool:
        return time.time() - self.created_at > QR_TTL


class QrService:
    def __init__(self):
        self._sessions: dict[str, QrSession] = {}

    def start(self, user_id: str) -> tuple[bool, str, Optional[QrSession]]:
        """创建二维码会话"""
        # 关键：创建和查询必须用同一个 device_id，否则米游社判定设备不一致直接风控
        device_id = new_device_id()
        try:
            login_url, ticket = create_qr(device_id)
        except QrLoginError as e:
            return False, f"获取二维码失败：{e.message}", None

        session = QrSession(
            user_id=user_id,
            ticket=ticket,
            device_id=device_id,
            login_url=login_url,
            image_url=qr_image_url(login_url),
        )
        self._sessions[user_id] = session
        logger.info(f"用户 {user_id} 发起扫码登录")

        text = (
            "请用【米游社 App】扫描二维码并在手机上确认登录\n"
            f"有效期约 {QR_TTL // 60} 分钟，扫完发送 #星铁扫码状态 完成绑定\n"
            f"若二维码无法显示，可在浏览器打开：\n{login_url}"
        )
        return True, text, session

    def check(self, user_id: str) -> tuple[bool, str]:
        """查询一次扫码状态；确认后直接完成绑定"""
        session = self._sessions.get(user_id)
        if not session:
            return False, "没有进行中的扫码，请先发送 #星铁扫码登录"

        if session.expired():
            self._sessions.pop(user_id, None)
            return False, "二维码已过期，请重新发送 #星铁扫码登录"

        # 轮询也不能太密，否则容易被风控
        elapsed = time.time() - session.last_poll_at
        if session.last_poll_at and elapsed < QR_POLL_INTERVAL:
            return False, "查询太频繁，请几秒后再试"
        session.last_poll_at = time.time()

        try:
            status, cookies = query_qr(session.ticket, session.device_id)
        except QrLoginError as e:
            # 只有真的失效才丢弃会话，风控/网络抖动让用户重试即可
            if e.retcode in (QR_RETCODE_EXPIRED, QR_RETCODE_CANCELLED):
                self._sessions.pop(user_id, None)
            logger.warn(f"用户 {user_id} 查询扫码状态失败: [{e.retcode}] {e.message}")
            return False, e.message

        session.status = status

        if status == QR_STATUS_SCANNED:
            return True, "已扫码，请在手机上点击「确认登录」"
        if status != QR_STATUS_CONFIRMED:
            return True, "还没有扫码，请用米游社 App 扫描二维码"

        # 已确认：拼 Cookie 并完成绑定
        try:
            cookie = build_cookie_string(cookies)
        except QrLoginError as e:
            self._sessions.pop(user_id, None)
            return False, f"获取凭证失败：{e.message}"

        self._sessions.pop(user_id, None)
        ok, msg = bind_service.bind_cookie(user_id, cookie)
        if ok:
            logger.info(f"用户 {user_id} 扫码登录并绑定成功")
            return True, "扫码登录成功！\n\n" + msg
        return False, msg

    def cancel(self, user_id: str) -> tuple[bool, str]:
        if self._sessions.pop(user_id, None):
            return True, "已取消本次扫码登录"
        return False, "当前没有进行中的扫码"


qr_service = QrService()
