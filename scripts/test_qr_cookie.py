"""
单元检查：二维码登录的 Set-Cookie 解析
回归目标：requests 的 resp.headers 是 CaseInsensitiveDict，没有 get_all，
         曾因此抛 AttributeError 导致扫码确认后插件直接崩掉。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class FakeRaw:
    def __init__(self, values):
        self.values = values
        self.headers = self

    def get_all(self, name, default=None):
        return list(self.values) if name == "Set-Cookie" else default


class FakeCookies(dict):
    pass


class FakeResp:
    """最小化模拟 requests.Response"""

    def __init__(self, header_lines, parsed=None):
        self.headers = {"Content-Type": "application/json"}
        self.cookies = FakeCookies(parsed or {})
        self.raw = FakeRaw(header_lines)


def check(name, resp, must_have):
    from core.api.qr_login import _parse_set_cookie

    got = _parse_set_cookie(resp)
    missing = [k for k in must_have if not got.get(k)]
    ok = not missing
    print(f"[{'OK' if ok else 'FAIL'}] {name} -> {sorted(got.keys())}")
    return ok


def main():
    all_ok = True

    # 场景1：多个 Set-Cookie 只存在于原始响应头（cookies 为空）
    r1 = FakeResp([
        "ltoken_v2=v2_abc; Path=/; HttpOnly",
        "ltmid_v2=12345_mid; Path=/; HttpOnly",
        "cookie_token_v2=ct_v2; Path=/",
    ])
    all_ok &= check("原始头多条 Set-Cookie", r1, ["ltoken_v2", "ltmid_v2", "cookie_token_v2"])

    # 场景2：requests 已解析进 CookieJar
    r2 = FakeResp([], {"ltoken_v2": "v2_x", "ltmid_v2": "9_mid"})
    all_ok &= check("仅 CookieJar", r2, ["ltoken_v2", "ltmid_v2"])

    # 场景3：两条来源都有，不应互相覆盖出错
    r3 = FakeResp(["ltoken_v2=v2_a; Path=/"], {"ltoken_v2": "v2_a", "ltmid_v2": "1_mid"})
    all_ok &= check("两者并存", r3, ["ltoken_v2", "ltmid_v2"])

    # 场景4：空响应不炸
    r4 = FakeResp([])
    all_ok &= check("空响应", r4, [])

    # 关键：绝不能因为 get_all 不存在而抛异常
    print("结论:", "通过" if all_ok else "存在问题")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
