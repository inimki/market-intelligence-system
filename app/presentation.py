from datetime import datetime
from zoneinfo import ZoneInfo


def format_beijing_time(value: datetime | None, format_string: str = "%Y-%m-%d %H:%M") -> str:
    """把数据库中的 UTC 时间统一显示为北京时间。"""
    if value is None:
        return "—"
    return value.astimezone(ZoneInfo("Asia/Shanghai")).strftime(format_string)
