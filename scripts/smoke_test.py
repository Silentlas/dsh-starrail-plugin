"""
协议冒烟测试
模拟 roost 核心：向插件 stdin 喂 NDJSON，读 stdout 校验协议合规性

用法（项目根目录，解释器需已装 requests）：
    python scripts/smoke_test.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.py"

INIT = {
    "t": "init",
    "protocol": 1,
    "id": "dsh-starrail",
    "config": {},
    "levels": {"base": 30, "end": 39},
    "coreLevels": {"owner": 0, "admin": 1, "manager": 2, "helper": 3},
    "prefix": "/",
    "dataDir": str(ROOT / "data"),
}


def msg(seq: int, content: str, user: str = "u1", group: str = "", command: str = "",
        args=None, is_command: bool = False):
    return {
        "t": "msg",
        "seq": seq,
        "msg": {
            "id": f"m{seq}", "kind": "group" if group else "c2c", "group": group,
            "user": user, "name": "测试用户", "content": content,
            "command": command, "args": args or [],
            "mentioned": False, "isCommand": is_command, "level": 32,
        },
    }


CASES = [
    ("接入帮助（# 前缀被动）", msg(1, "#星铁帮助")),
    ("命令形式（/ 前缀）", msg(2, "星铁帮助", command="星铁帮助", is_command=True)),
    ("未绑定查体力", msg(3, "#星铁体力", user="u_not_bind")),
    ("群聊绑定Cookie被拦截", msg(4, "#星铁绑定ck ltoken_v2=x", group="g1", user="u2")),
    ("绑定参数缺失", msg(5, "星铁绑定ck", user="u3", command="星铁绑定ck", is_command=True)),
    ("解绑但未绑定", msg(6, "#星铁解绑", user="u4")),
    ("开发中功能", msg(7, "#星铁角色 黄泉", user="u5")),
    ("普通闲聊（应只回handled）", msg(8, "今天天气不错")),
    ("无效Cookie", msg(9, "#星铁绑定ck ltoken_v2=fake; ltuid_v2=1", user="u6")),
]


def main():
    payload = "\n".join(json.dumps(o, ensure_ascii=False) for o in [INIT] + [c for _, c in CASES])
    payload += '\n' + json.dumps({"t": "shutdown"}) + "\n"

    proc = subprocess.run(
        [sys.executable, str(MAIN)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
        timeout=120,
    )

    print("=== stdout（协议通道）===")
    replies = {}
    ready = None
    bad_lines = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad_lines.append(line)
            continue
        t = obj.get("t")
        if t == "ready":
            ready = obj
        elif t == "reply":
            replies.setdefault(obj.get("seq"), []).append(obj.get("text") or f"[image]{obj.get('image')}")
        elif t == "error":
            print(f"  !! error 协议消息: {obj.get('msg')}")

    print(f"ready: {'已返回' if ready else '未返回'}")
    if ready:
        cmds = [c["name"] for c in ready.get("commands", [])]
        print(f"  命令: {cmds}")
        print(f"  菜单组: {[m['title'] for m in ready.get('menus', [])]}")

    print("\n=== 用例结果 ===")
    idx = 0
    for title, m in CASES:
        idx += 1
        got = replies.get(m["seq"])
        if got:
            text = got[0].replace("\n", " | ")[:110]
            print(f"[{idx}] {title}\n    -> {text}")
        else:
            print(f"[{idx}] {title}\n    -> (无回复)")

    print("\n=== 协议合规检查 ===")
    print(f"stdout 非法行: {len(bad_lines)}")
    for b in bad_lines[:3]:
        print(f"  非法: {b[:100]}")
    print(f"stderr 行数: {len(proc.stderr.splitlines())}")
    print("stderr 末 6 行:")
    for l in proc.stderr.splitlines()[-6:]:
        print("  " + l)

    ok = bool(ready) and not bad_lines and all(
        replies.get(m["seq"]) for i, (_, m) in enumerate(CASES) if i != 7
    )
    # 第 8 个用例（普通闲聊）必须没有回复，否则会刷屏
    no_reply_case_ok = not replies.get(CASES[7][1]["seq"])
    if not no_reply_case_ok:
        print("  !! 普通闲聊被错误回复，会刷屏")
    ok = ok and no_reply_case_ok
    print("\n结论:", "通过" if ok else "存在问题，见上")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
