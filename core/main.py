"""
星穹铁道助手核心服务
基于 FastAPI 提供HTTP接口，供DSH桥接层调用
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional

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
    # 临时测试响应
    if req.command == "#星铁帮助":
        return CommandResponse(
            success=True,
            message="=== 星穹铁道助手 ===\n#星铁绑定ck - 私聊绑定Cookie\n#星铁体力 - 查询体力\n#星铁角色 <角色名> - 查询练度\n#星铁抽卡分析 - 查看抽卡统计"
        )
    return CommandResponse(
        success=False,
        message=f"未知指令: {req.command}"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
