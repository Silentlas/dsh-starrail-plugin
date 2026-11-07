"""
dsh-starrail-plugin —— dsh-roost 外部 Python 插件入口
协议：stdin 一行一个 JSON / stdout 一行一个 JSON（NDJSON）
调试输出一律走 stderr 或 log 协议消息，绝不能打到 stdout
"""
import sys
import traceback
from pathlib import Path

from roost_sdk import Plugin

from core.router import Request, handle
from core.utils.logger import Logger
from core.utils.store import init_store

logger = Logger("StarRail")

PLUGIN_ID = "dsh-starrail"

p = Plugin(id=PLUGIN_ID, name="星穹铁道助手", version="0.1.0")

p.menu("星穹铁道", [
    {"text": "#星铁体力", "desc": "查询开拓力、委托与每日实训进度"},
    {"text": "#星铁绑定ck", "desc": "私聊绑定米游社 Cookie（建议用小号）"},
])


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


@p.command("星铁帮助", desc="查看星穹铁道助手指令", alias=["星铁help", "星铁"])
def cmd_help(m) -> None:
    m.reply(handle(Request(
        user_id=m.user, group_id=m.group, is_group=bool(m.group),
        command="星铁帮助", args=[],
    )).text)


@p.command("星铁绑定ck <cookie>", desc="私聊绑定米游社 Cookie")
def cmd_bind(m) -> None:
    result = handle(Request(
        user_id=m.user, group_id=m.group, is_group=bool(m.group),
        command="星铁绑定ck", args=list(m.args),
    ))
    m.reply(result.text)


@p.command("星铁解绑", desc="解除已绑定的米游社账号")
def cmd_unbind(m) -> None:
    result = handle(Request(
        user_id=m.user, group_id=m.group, is_group=bool(m.group),
        command="星铁解绑", args=[],
    ))
    m.reply(result.text)


@p.command("星铁体力", desc="查询开拓力、委托与每日实训")
def cmd_stamina(m) -> None:
    result = handle(Request(
        user_id=m.user, group_id=m.group, is_group=bool(m.group),
        command="星铁体力", args=[],
    ))
    if result.image:
        m.reply_image(result.image)
    m.reply(result.text)


def on_any_message(m):
    """
    被动兜底：roost 命令前缀默认是 /，而星铁社区习惯用 #
    这里让 #星铁体力 这种写法也能触发
    """
    if not m.content or not m.content.lstrip().startswith(("#", "！", "!")):
        return False

    result = handle(Request(
        user_id=m.user, group_id=m.group, is_group=bool(m.group),
        command="", args=[], content=m.content,
    ))
    if not result.text:
        return False
    m.reply(result.text)
    return True


def main() -> None:
    """接管 roost 主循环，同时挂上 init 钩子"""
    # SDK 的 run() 内部收到 init 时调用 _ready，这里包一层以捕获 dataDir
    import json
    from roost_sdk import _send

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
    # 配置在 init 里下发前，先用默认位置建库，避免 command 先到时报错
    init_store(None)
    main()
