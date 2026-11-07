"""
验证 stoken 换 ltoken / cookie_token 的接口形态（用假 stoken，只看错误码判断端点是否正确）。
端点对、参数对时，假 stoken 会返回登录类错误（-100 / 10001），
不是 404 / invalid request / 参数错误。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests  # noqa: E402

from core.api.config import (  # noqa: E402
    URL_LTOKEN_BY_STOKEN, URL_COOKIE_BY_STOKEN, URL_STOKEN_V2_BY_V1,
    URL_S_TOKEN_BY_GAME_TOKEN, GAME_QR_APP_ID, URL_GAME_QR_FETCH, URL_GAME_QR_QUERY,
)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 miHoYoBBS/2.76.1")

print("== 取码 / 查码端点 ==")
import uuid  # noqa: E402
device = str(uuid.uuid4()).upper()
r = requests.post(URL_GAME_QR_FETCH, json={"app_id": GAME_QR_APP_ID, "device": device},
                  headers={"Content-Type": "application/json", "x-rpc-app_id": "bll8iq97cem8",
                           "User-Agent": UA}, timeout=15).json()
print(f"  fetch -> retcode={r.get('retcode')} app_name 来自 url={str((r.get('data') or {}).get('url'))[:60]}")
ticket = (r.get("data") or {}).get("url", "")[-24:]
q = requests.post(URL_GAME_QR_QUERY, json={"app_id": GAME_QR_APP_ID, "device": device, "ticket": ticket},
                  headers={"Content-Type": "application/json", "x-rpc-app_id": "bll8iq97cem8",
                           "User-Agent": UA}, timeout=15).json()
print(f"  query(未扫码) -> retcode={q.get('retcode')} status={(q.get('data') or {}).get('status')}")

print("\n== stoken 换凭证端点（假 stoken）==")
for name, url in (("getLTokenBySToken", URL_LTOKEN_BY_STOKEN),
                  ("getCookieAccountInfoBySToken", URL_COOKIE_BY_STOKEN)):
    d = requests.get(url, params={"stoken": "fake-stoken", "uid": "123456789"},
                     headers={"User-Agent": UA}, timeout=15).json()
    print(f"  {name} -> retcode={d.get('retcode')} message={str(d.get('message') or '')[:40]}")

d = requests.post(URL_STOKEN_V2_BY_V1, json={"stoken": "fake", "mid": "123456789"},
                  headers={"Content-Type": "application/json", "x-rpc-app_id": "bll8iq97cem8",
                           "Referer": "https://app.mihoyo.com", "User-Agent": UA}, timeout=15).json()
print(f"  getTokenBySToken(v2) -> retcode={d.get('retcode')} message={str(d.get('message') or '')[:40]}")

d = requests.post(URL_S_TOKEN_BY_GAME_TOKEN, json={"account_id": 123456789, "game_token": "fake"},
                 headers={"Content-Type": "application/json", "x-rpc-app_id": "bll8iq97cem8",
                          "Referer": "https://app.mihoyo.com", "User-Agent": UA}, timeout=15).json()
print(f"  getTokenByGameToken -> retcode={d.get('retcode')} message={str(d.get('message') or '')[:40]}")
