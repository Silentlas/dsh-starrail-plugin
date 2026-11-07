"""
账号绑定服务
Cookie绑定、校验、存储
"""
from ..api.client import MhyClient, MhyApiError
from ..api.config import RECORD_API, GAME_ID
from ..utils.store import store
from ..utils.logger import Logger

logger = Logger("BindService")


class BindService:
    def __init__(self):
        self.store = store

    def bind_cookie(self, qq_id: str, cookie: str) -> tuple[bool, str]:
        """
        绑定米游社Cookie
        返回: (成功与否, 提示信息)
        """
        # 先校验Cookie有效性
        try:
            client = MhyClient(cookie)
            # 调用一个轻量接口校验
            url = f"{RECORD_API}/game_record/widget/v2/widget"
            data = client.get(url, params={"game_id": GAME_ID})
            # 校验成功，提取uid
            uid = data.get("region", "")
            # TODO: 实际提取UID的逻辑，等接口对接后补充

            # 存储
            self.store.set_user_bind(qq_id, {
                "cookie": cookie,
                "uid": uid or None
            })
            logger.info(f"用户 {qq_id} 绑定Cookie成功")
            return True, "绑定成功！现在可以使用 #星铁体力 查询你的账号信息了"
        except MhyApiError as e:
            logger.warn(f"用户 {qq_id} Cookie校验失败: {e.message}")
            return False, f"Cookie校验失败：{e.message}，请检查后重新输入"
        except Exception as e:
            logger.error("绑定Cookie失败", e)
            return False, "绑定失败，请稍后重试"

    def get_user_bind(self, qq_id: str):
        """获取用户绑定信息"""
        return self.store.get_user_bind(qq_id)

    def unbind(self, qq_id: str) -> tuple[bool, str]:
        """解绑账号"""
        bind = self.get_user_bind(qq_id)
        if not bind:
            return False, "你还没有绑定账号"
        self.store.remove_user_bind(qq_id)
        logger.info(f"用户 {qq_id} 解绑成功")
        return True, "解绑成功！所有绑定信息已删除"

    def get_client(self, qq_id: str) -> tuple[MhyClient | None, str]:
        """获取已绑定的API客户端，未绑定返回错误提示"""
        bind = self.get_user_bind(qq_id)
        if not bind or not bind.cookie:
            return None, "你还没有绑定米游社Cookie，请先发送 #星铁绑定ck 绑定"
        return MhyClient(bind.cookie), ""


bind_service = BindService()
