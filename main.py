"""
dsh-starrail-plugin —— dsh-roost 外部 Python 插件入口
协议：stdin 一行一个 JSON / stdout 一行一个 JSON（NDJSON）
调试输出一律走 stderr 或 log 协议消息，绝不能打到 stdout
"""
import json
import sys
import traceback
from pathlib import Path

from roost_sdk import Plugin, _send

from core.router import Request, handle
from core.utils.logger import Logger
from core.utils.store import init_store

logger = Logger("StarRail")

PLUGIN_ID = "dsh-starrail"


class StarrailPlugin(Plugin):
    """
    在原 SDK 基础上补两件事：
    1. ready 里声明 listen — SDK 没暴露这个字段，不声明的话 roost 不会
       把非命令消息转发过来，被动监听形同虚设
    2. 命令别名用独立装饰器注册，不要用 SDK 的 alias：alias 条目上报的
       pattern 仍是原始命令名，roost 按 pattern 解析命令名会判定重复注册
    """

    def _ready(self) -> None:
        _send({
            "t": "ready",
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "commands": [
                {"name": k, "desc": v["desc"], "pattern": v["pattern"]}
                for k, v in self._commands.items()
            ],
            "menus": self._menus,
            "levels": self.levels,
            "listen": ["message"],
        })


p = StarrailPlugin(id=PLUGIN_ID, name="星穹铁道助手", version="0.1.0")

p.menu("星穹铁道", [
    {"text": "#星铁扫码登录", "desc": "米游社扫码绑定（私聊）"},
    {"text": "#星铁体力", "desc": "查询开拓力、委托与每日实训进度"},
    {"text": "#星铁绑定ck", "desc": "私聊粘贴米游社 Cookie（建议用小号）"},
])


def _run(user: str, group: str, command: str, args=None, content: str = ""):
    return handle(Request(
        user_id=user, group_id=group or "", is_group=bool(group),
        command=command, args=args or [], content=content,
    ))


def _reply(m, result) -> None:
    if result.image:
        m.reply_image(result.image)
    if result.text:
        m.reply(result.text)


@p.command("星铁帮助", desc="查看星穹铁道助手指令")
def cmd_help(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁帮助"))


@p.command("星铁help", desc="查看星穹铁道助手指令")
def cmd_help_en(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁帮助"))


@p.command("星铁", desc="查看星穹铁道助手指令")
def cmd_bare(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁帮助"))


@p.command("星铁扫码登录", desc="米游社扫码绑定（私聊，二维码有效期约 4 分钟）")
def cmd_qr_login(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁扫码登录"))


@p.command("星铁扫码状态", desc="查询扫码结果，确认后自动完成绑定")
def cmd_qr_status(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁扫码状态"))


@p.command("星铁取消扫码", desc="取消本次扫码登录")
def cmd_qr_cancel(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁取消扫码"))


@p.command("星铁绑定ck <cookie>", desc="私聊绑定米游社 Cookie")
def cmd_bind(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁绑定ck", m.args))


@p.command("星铁解绑", desc="解除已绑定的米游社账号")
def cmd_unbind(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁解绑"))


@p.command("星铁体力", desc="查询开拓力、委托与每日实训")
def cmd_stamina(m) -> None:
    _reply(m, _run(m.user, m.group, "星铁体力"))


def on_any_message(m):
    """
    被动兜底：roost 命令前缀默认是 /，而星铁社区习惯用 #
    这里让 #星铁体力 这种写法也能触发；非星铁消息返回 False 交给别的插件
    """
    if not m.content or not m.content.lstrip().startswith(("#", "！", "!")):
        return False

    result = _run(m.user, m.group, "", content=m.content)
    if not result.text and not result.image:
        return False
    # 必须走 _reply：这里直接 m.reply(text) 会把 result.image 丢掉，
    # 表现为「被动分支不发图、命令分支能发图」这种一半好用的故障
    _reply(m, result)
    return True


def _on_init(info: dict) -> None:
    """roost 下发运行信息后，把数据库指到插件专属目录"""
    data_dir = info.get("dataDir")
    if data_dir:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        init_store(data_dir)
        logger.info(f"数据目录已设置: {data_dir}")
    else:
        init_store(None)
        logger.warn("未收到 dataDir，使用项目内 data/ 目录")


def main() -> None:
    """接管主循环，以便在 init 时捕获 dataDir"""
    p.on_message(on_any_message)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.warn(f"收到无法解析的行: {line[:80]}")
            continue

        t = obj.get("t")
        try:
            if t == "init":
                if isinstance(obj.get("config"), dict):
                    p.config.update(obj["config"])
                _on_init(obj)
                p._ready()
            elif t == "msg":
                p._handle(obj)
            elif t == "shutdown":
                logger.info("收到 shutdown，插件退出")
                break
        except Exception:
            logger.error("处理消息异常:\n" + traceback.format_exc(limit=3))
            if t == "msg" and "seq" in obj:
                _send({"t": "handled", "seq": obj["seq"]})


if __name__ == "__main__":
    # init 之前先建默认库，避免消息先到时存储未初始化
    init_store(None)
    main()
