"""
账号绑定服务
Cookie 校验 → 自动拉取星铁 UID/区服/昵称 → 持久化
"""
from typing import Optional

from ..api.client import MhyApiError, MhyClient
from ..api.record import get_game_roles
from ..utils.logger import Logger
from ..utils.store import UserBind, store

logger = Logger("BindService")


class BindService:
    def __init__(self):
        self.store = store

    def bind_cookie(self, qq_id: str, cookie: str) -> tuple[bool, str]:
        """
        绑定米游社 Cookie
        会先校验 Cookie 并拉取绑定的星铁角色，再落库
        """
        cookie = cookie.strip()
        if "ltoken" not in cookie and "cookie_token" not in cookie:
            return False, "Cookie 格式不正确，应包含 ltoken_v2 / ltuid_v2 等字段，请重新复制完整 Cookie"

        try:
            client = MhyClient(cookie)
            roles = get_game_roles(client)
        except MhyApiError as e:
            logger.warn(f"用户 {qq_id} Cookie 校验失败: {e.message}")
            return False, f"Cookie 校验失败：{e.message}"
        except Exception as e:
            logger.error("绑定 Cookie 时发生未预期错误", e)
            return False, "绑定失败，请稍后重试"

        if not roles:
            return False, "该 Cookie 下没有查询到星铁角色，请确认已绑定星铁账号"

        role = next((r for r in roles if r.is_chosen), roles[0])
        self.store.set_user_bind(qq_id, {
            "cookie": cookie,
            "uid": role.game_uid,
            "region": role.region,
            "nickname": role.nickname,
        })
        logger.info(f"用户 {qq_id} 绑定成功: uid={role.game_uid} region={role.region}")

        extra = ""
        if len(roles) > 1:
            extra = f"\n（检测到 {len(roles)} 个角色，已默认绑定 {role.nickname}）"
        return True, (
            f"绑定成功！\n开拓者：{role.nickname}\nUID：{role.game_uid}\n"
            f"区服：{role.region_name or role.region}{extra}\n\n"
            f"现在可以发送 #星铁体力 查询实时状态"
        )

    def get_user_bind(self, qq_id: str) -> Optional[UserBind]:
        return self.store.get_user_bind(qq_id)

    def unbind(self, qq_id: str) -> tuple[bool, str]:
        if not self.get_user_bind(qq_id):
            return False, "你还没有绑定账号，发送 #星铁绑定ck 进行绑定"
        self.store.remove_user_bind(qq_id)
        logger.info(f"用户 {qq_id} 解绑成功")
        return True, "解绑成功，绑定信息已删除"

    def get_client(self, qq_id: str) -> tuple[Optional[MhyClient], Optional[UserBind], str]:
        """
        获取已绑定的客户端
        返回 (client, bind, 错误提示)；成功时错误提示为空字符串
        """
        bind = self.get_user_bind(qq_id)
        if not bind or not bind.cookie:
            return None, None, "你还没有绑定米游社 Cookie，请私聊发送 #星铁绑定ck 进行绑定"
        return MhyClient(bind.cookie), bind, ""


bind_service = BindService()
