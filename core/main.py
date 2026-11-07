"""
星穹铁道助手核心服务
基于 FastAPI 提供HTTP接口，供DSH桥接层调用
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional

from .bind.service import bind_service
from .utils.ratelimit import rate_limiter
from .utils.logger import Logger

logger = Logger("StarRailCore")

app = FastAPI(title="StarRail Plugin Core", version="0.1.0")


# 请求模型
class CommandRequest(BaseModel):
    qq_id: str
    group_id: Optional[str] = None
    command: str
    args: str
    is_group: bool = False


# 响应模型
class CommandResponse(BaseModel):
    success: bool
    message: str
    image: Optional[str] = None  # base64图片，可选


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/command", response_model=CommandResponse)
async def handle_command(req: CommandRequest):
    """处理从DSH桥接层发来的指令"""
    # 频率限制
    if req.is_group:
        if not rate_limiter.check_group(req.group_id):
            return CommandResponse(success=False, message="当前群请求过于频繁，请稍后再试")
    if not rate_limiter.check_user(req.qq_id):
        return CommandResponse(success=False, message="你操作太频繁了，请1分钟后再试")

    command = req.command.strip()
    args = req.args.strip()

    # 帮助命令
    if command == "#星铁帮助":
        return CommandResponse(
            success=True,
            message="""=== 星穹铁道助手 ===
【账号相关】
#星铁绑定ck <Cookie> - 私聊绑定米游社Cookie
#星铁解绑 - 删除绑定信息
【查询功能】
#星铁体力 - 查询当前体力
#星铁角色 <角色名> - 查询角色练度
#星铁抽卡分析 - 查看抽卡统计

⚠️ 提示：Cookie绑定请在私聊中进行，群聊禁止发送敏感信息"""
        )

    # 绑定Cookie
    elif command == "#星铁绑定ck":
        if req.is_group:
            return CommandResponse(success=False, message="⚠️ 为了你的账号安全，Cookie绑定请在私聊中进行")
        if not args:
            return CommandResponse(success=False, message="请输入要绑定的Cookie，格式：#星铁绑定ck <你的Cookie>")
        ok, msg = bind_service.bind_cookie(req.qq_id, args)
        return CommandResponse(success=ok, message=msg)

    # 解绑
    elif command == "#星铁解绑":
        ok, msg = bind_service.unbind(req.qq_id)
        return CommandResponse(success=ok, message=msg)

    # 未实现的命令
    else:
        return CommandResponse(success=False, message=f"指令 {command} 暂未实现，输入 #星铁帮助 查看可用命令")


if __name__ == "__main__":
    logger.info("星穹铁道核心服务启动中...")
    uvicorn.run(app, host="127.0.0.1", port=8765)
