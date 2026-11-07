"""
星穹铁道助手核心服务
基于 FastAPI 提供 HTTP 接口，供 DSH 桥接层调用
"""
from typing import Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from .api.client import MhyApiError
from .api.record import format_note, get_note, parse_note
from .bind.service import bind_service
from .utils.logger import Logger
from .utils.ratelimit import rate_limiter

logger = Logger("StarRailCore")

app = FastAPI(title="StarRail Plugin Core", version="0.1.0")

HELP_TEXT = """=== 星穹铁道助手 ===
【账号】
#星铁绑定ck <Cookie> - 私聊绑定米游社 Cookie
#星铁解绑 - 删除绑定信息
【查询】
#星铁体力 - 查询开拓力 / 委托 / 实训
#星铁角色 <角色名> - 查询角色练度（开发中）
#星铁抽卡分析 - 抽卡统计（开发中）

提示：Cookie 属于敏感信息，绑定请务必在私聊中进行"""


class CommandRequest(BaseModel):
    qq_id: str
    group_id: Optional[str] = None
    command: str
    args: str = ""
    is_group: bool = False


class CommandResponse(BaseModel):
    success: bool
    message: str
    image: Optional[str] = None


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


def _handle_stamina(req: CommandRequest) -> CommandResponse:
    """体力查询"""
    client, bind, error = bind_service.get_client(req.qq_id)
    if error:
        return CommandResponse(success=False, message=error)

    try:
        raw = get_note(client, bind.uid, bind.region)
    except MhyApiError as e:
        logger.warn(f"查询体力失败 qq={req.qq_id}: {e.message}")
        return CommandResponse(success=False, message=f"查询失败：{e.message}")

    note = parse_note(raw)
    text = format_note(note, bind.nickname or "")
    return CommandResponse(success=True, message=text)


@app.post("/api/command", response_model=CommandResponse)
async def handle_command(req: CommandRequest):
    """处理从 DSH 桥接层发来的指令"""
    # 频率限制
    if req.is_group and req.group_id:
        if not rate_limiter.check_group(req.group_id):
            return CommandResponse(success=False, message="本群请求过于频繁，请稍后再试")
    if not rate_limiter.check_user(req.qq_id):
        return CommandResponse(success=False, message="操作太频繁了，请 1 分钟后再试")

    command = req.command.strip()
    args = req.args.strip()

    if command == "#星铁帮助":
        return CommandResponse(success=True, message=HELP_TEXT)

    if command == "#星铁绑定ck":
        if req.is_group:
            return CommandResponse(success=False,
                                   message="为了账号安全，Cookie 绑定请在私聊中进行")
        if not args:
            return CommandResponse(success=False,
                                   message="请提供 Cookie，格式：#星铁绑定ck <你的Cookie>")
        ok, msg = bind_service.bind_cookie(req.qq_id, args)
        return CommandResponse(success=ok, message=msg)

    if command == "#星铁解绑":
        ok, msg = bind_service.unbind(req.qq_id)
        return CommandResponse(success=ok, message=msg)

    if command == "#星铁体力":
        return _handle_stamina(req)

    return CommandResponse(success=False,
                           message=f"指令 {command} 暂未实现，发送 #星铁帮助 查看可用命令")


if __name__ == "__main__":
    logger.info("星穹铁道核心服务启动中...")
    uvicorn.run(app, host="127.0.0.1", port=8765)
