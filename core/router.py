"""
命令路由层
与传输方式无关：roost 插件入口、本地测试都调用这里的 handle()
"""
import re
from dataclasses import dataclass
from typing import Optional

from .api.client import MhyApiError
from .api.record import format_note, get_note, parse_note
from .bind.qr_service import qr_service
from .bind.service import bind_service
from .utils.logger import Logger
from .utils.ratelimit import rate_limiter

logger = Logger("Router")

COMMAND_PREFIXES = ("#", "/", "！", "!")

HELP_TEXT = """=== 星穹铁道助手 ===
【账号】
#星铁扫码登录 - 米游社扫码绑定（推荐，私聊）
#星铁扫码状态 - 查看扫码结果并完成绑定
#星铁绑定ck <Cookie> - 手动粘贴 Cookie 绑定
#星铁解绑 - 删除绑定信息
【查询】
#星铁体力 - 开拓力 / 委托 / 实训
#星铁角色 <角色名> - 角色练度（开发中）
#星铁抽卡分析 - 抽卡统计（开发中）

Cookie 属于敏感信息，绑定请务必在私聊中进行"""


@dataclass
class Request:
    """一条待处理的用户请求"""
    user_id: str
    group_id: str = ""
    is_group: bool = False
    command: str = ""
    args: Optional[list] = None
    content: str = ""


@dataclass
class Result:
    """处理结果"""
    ok: bool
    text: str
    image: Optional[str] = None


def parse_command(content: str) -> tuple[str, list[str]]:
    """
    从正文里解析出「星铁XXX」形式的命令与参数
    支持 #星铁体力、/星铁体力、星铁体力、#星铁角色 黄泉
    """
    text = (content or "").strip()
    for p in COMMAND_PREFIXES:
        if text.startswith(p):
            text = text[len(p):].strip()
            break

    parts = re.split(r"\s+", text) if text else []
    if not parts:
        return "", []

    head = parts[0]
    if not head.startswith("星铁"):
        return "", []
    return head, parts[1:]


def _require_bind(user_id: str):
    """取已绑定的客户端，未绑定返回错误文案"""
    client, bind, error = bind_service.get_client(user_id)
    if error:
        return None, None, error
    return client, bind, ""


def _handle_stamina(req: Request) -> Result:
    client, bind, error = _require_bind(req.user_id)
    if error:
        return Result(False, error)

    try:
        raw = get_note(client, bind.uid, bind.region)
    except MhyApiError as e:
        logger.warn(f"查询体力失败 user={req.user_id}: {e.message}")
        return Result(False, f"查询失败：{e.message}")

    note = parse_note(raw)
    return Result(True, format_note(note, bind.nickname or ""))


def handle(req: Request) -> Result:
    """
    统一入口
    返回 Result；未识别为星铁命令时返回 None 之外的空命令由调用方决定是否忽略
    """
    command = (req.command or "").strip()
    args = req.args or []

    if not command:
        command, args = parse_command(req.content)

    if not command:
        return Result(False, "")

    # 频率限制：群聊同时限制群维度
    if req.is_group and req.group_id and not rate_limiter.check_group(req.group_id):
        return Result(False, "本群请求过于频繁，请稍后再试")
    if not rate_limiter.check_user(req.user_id):
        return Result(False, "操作太频繁了，请 1 分钟后再试")

    if command in ("星铁帮助", "星铁help", "星铁"):
        return Result(True, HELP_TEXT)

    if command in ("星铁扫码登录", "星铁扫码"):
        if req.is_group:
            return Result(False, "扫码会暴露你的登录二维码，请在私聊中进行")
        ok, text, session = qr_service.start(req.user_id)
        image = session.image_url if session else None
        return Result(ok, text, image=image)

    if command == "星铁扫码状态":
        ok, text = qr_service.check(req.user_id)
        return Result(ok, text)

    if command in ("星铁取消扫码", "星铁扫码取消"):
        ok, text = qr_service.cancel(req.user_id)
        return Result(ok, text)

    if command in ("星铁绑定ck", "星铁绑定CK", "星铁绑定"):
        if req.is_group:
            return Result(False, "为了账号安全，Cookie 绑定请在私聊中进行")
        cookie = " ".join(args).strip()
        if not cookie:
            return Result(False, "请提供 Cookie，格式：#星铁绑定ck <你的Cookie>")
        ok, msg = bind_service.bind_cookie(req.user_id, cookie)
        return Result(ok, msg)

    if command == "星铁解绑":
        ok, msg = bind_service.unbind(req.user_id)
        return Result(ok, msg)

    if command in ("星铁体力", "星铁开拓力"):
        return _handle_stamina(req)

    if command in ("星铁角色", "星铁练度", "星铁抽卡分析", "星铁抽卡"):
        return Result(False, f"{command} 功能正在开发中，敬请期待")

    return Result(False, f"未知指令：{command}\n发送 #星铁帮助 查看可用命令")
