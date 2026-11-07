"""
诊断脚本：直接复现 QQ 官方机器人的富媒体上传接口，判断「远程 URL 取图」这一步是否可行。
只上传不发送（srv_send_msg=false），不会在会话里产生任何消息。
不打印任何密钥。

用法：
    set QQ_OPENID=<你的 c2c openid>   # 可留空，仅用于构造接口路径
    python scripts/probe_qq_media.py
"""
import json
import os
import sys
import uuid

import requests

sys.path.insert(0, r"D:\Personal data\星铁机器人")

BOT_CFG = r"C:\Users\admin\.dsh\dsh-roost\roost\config\bots\main.json"
OPENID = os.environ.get("QQ_OPENID", "")


def load_bot():
    with open(BOT_CFG, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    app_id = cfg.get("appId") or cfg.get("appid")
    secret = cfg.get("secret") or cfg.get("clientSecret") or cfg.get("appSecret")
    if not app_id or not secret:
        raise SystemExit("配置文件里没找到 appId / secret，字段名可能不同")
    return app_id, secret


def get_token(app_id: str, secret: str) -> str:
    r = requests.post("https://bots.qq.com/app/getAppAccessToken",
                      json={"appId": app_id, "clientSecret": secret}, timeout=15)
    body = r.json()
    token = body.get("access_token")
    if not token:
        raise SystemExit(f"取 token 失败: HTTP {r.status_code} {body.get('code')} {body.get('message')}")
    print(f"token 获取成功（长度 {len(token)}，不打印）")
    return token


def try_upload(app_id: str, token: str, url: str) -> None:
    headers = {
        "Authorization": f"QQBot {token}",
        "X-Union-Appid": app_id,
        "Content-Type": "application/json",
    }
    body = {"file_type": 1, "srv_send_msg": False, "url": url}
    r = requests.post(f"https://api.sgroup.qq.com/v2/users/{OPENID}/files",
                      headers=headers, json=body, timeout=20)
    print(f"\nURL: {url[:70]}...")
    print(f"HTTP {r.status_code}")
    try:
        data = r.json()
    except Exception:
        print("非 JSON 响应:", r.text[:200])
        return
    if data.get("file_info"):
        print("结果: 上传成功，拿到 file_info（长度 %d）" % len(data["file_info"]))
        print("      file_uuid =", str(data.get("file_uuid"))[:20], " ttl =", data.get("ttl"))
    else:
        print("结果: 失败 ->", json.dumps(data, ensure_ascii=False)[:300])


def main():
    app_id, secret = load_bot()
    print("appId =", app_id)
    token = get_token(app_id, secret)

    from core.api.qr_login import create_qr, new_device_id, qr_image_url
    login_url, _ = create_qr(new_device_id())
    print("\n已创建一张真实二维码登录链接")

    candidates = [
        qr_image_url(login_url),
        "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" + requests.utils.quote(login_url, safe=""),
        "https://quickchart.io/qr?size=300&text=" + requests.utils.quote(login_url, safe=""),
    ]
    for u in candidates:
        try_upload(app_id, token, u)


if __name__ == "__main__":
    main()
