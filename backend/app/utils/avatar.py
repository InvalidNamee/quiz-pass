def build_qq_avatar_url(email: str) -> str | None:
    lower = email.lower()
    if not lower.endswith("@qq.com"):
        return None
    qq_number = lower.removesuffix("@qq.com")
    if not qq_number.isdigit():
        return None
    return f"https://q1.qlogo.cn/g?b=qq&nk={qq_number}&s=100"
