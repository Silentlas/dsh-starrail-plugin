"""
星铁游戏记录接口
- 账号绑定关系（获取 UID / 区服）
- 实时便笺（开拓力、派遣、每日实训）
字段严格对齐 UIGF-org mihoyo-api-collection 文档
"""
from dataclasses import dataclass
from typing import Optional

from .client import MhyClient
from .config import DEFAULT_REGION, GAME_BIZ, URL_GET_ROLES_BY_COOKIE, URL_NOTE


@dataclass
class GameRole:
    """绑定的游戏角色"""
    game_biz: str
    region: str
    game_uid: str
    nickname: str
    level: int
    region_name: str
    is_official: bool
    is_chosen: bool


def get_game_roles(client: MhyClient) -> list[GameRole]:
    """
    获取 Cookie 对应的星铁绑定角色列表
    接口：GET /binding/api/getUserGameRolesByCookie?game_biz=hkrpg_cn
    需要 LToken（ltoken_v2 + ltmid_v2）
    """
    data = client.get(URL_GET_ROLES_BY_COOKIE, params={"game_biz": GAME_BIZ})
    roles = []
    for item in data.get("list", []):
        roles.append(GameRole(
            game_biz=item.get("game_biz", ""),
            region=item.get("region", ""),
            game_uid=str(item.get("game_uid", "")),
            nickname=item.get("nickname", ""),
            level=int(item.get("level", 0)),
            region_name=item.get("region_name", ""),
            is_official=bool(item.get("is_official", False)),
            is_chosen=bool(item.get("is_chosen", False)),
        ))
    return roles


def get_note(client: MhyClient, uid: str, region: str = DEFAULT_REGION) -> dict:
    """
    获取实时便笺（开拓力等）
    接口：GET /game_record/app/hkrpg/api/note?role_id=&server=
    返回原始 data 字典，字段见 format_note
    """
    return client.get(URL_NOTE, params={"role_id": uid, "server": region})


def _seconds_to_text(seconds: int) -> str:
    """秒数转 X小时Y分钟"""
    if seconds <= 0:
        return "已恢复满"
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}小时{minutes}分钟"
    return f"{minutes}分钟"


@dataclass
class NoteData:
    """实时便笺整理后的数据"""
    current_stamina: int
    max_stamina: int
    stamina_recover_time: int
    expeditions_finished: int
    expeditions_total: int
    current_train_score: int
    max_train_score: int
    train_score_recover_time: int
    daily_train_finished: Optional[int]
    daily_train_total: Optional[int]


def parse_note(raw: dict) -> NoteData:
    """把便笺原始返回转成结构化数据"""
    expeditions = raw.get("expeditions") or []
    finished = sum(1 for e in expeditions if e.get("status") == "Finished")
    daily = raw.get("daily_activity") or {}
    return NoteData(
        current_stamina=int(raw.get("current_stamina", 0)),
        max_stamina=int(raw.get("max_stamina", 0)),
        stamina_recover_time=int(raw.get("stamina_recover_time", 0) or 0),
        expeditions_finished=finished,
        expeditions_total=len(expeditions),
        current_train_score=int(raw.get("current_train_score", 0) or 0),
        max_train_score=int(raw.get("max_train_score", 0) or 0),
        train_score_recover_time=int(raw.get("train_score_recover_time", 0) or 0),
        daily_train_finished=daily.get("current_train_score"),
        daily_train_total=daily.get("max_train_score"),
    )


def format_note(note: NoteData, nickname: str = "") -> str:
    """格式化成 QQ 文本消息"""
    lines = []
    if nickname:
        lines.append(f"开拓者：{nickname}")
    lines.append(f"开拓力：{note.current_stamina}/{note.max_stamina}")
    lines.append(f"　回复：{_seconds_to_text(note.stamina_recover_time)}")
    lines.append(f"支援委托：{note.expeditions_finished}/{note.expeditions_total} 已完成")
    lines.append(f"每日实训：{note.current_train_score}/{note.max_train_score}")
    lines.append(f"　回复：{_seconds_to_text(note.train_score_recover_time)}")
    return "\n".join(lines)


def seconds_to_text(seconds: int) -> str:
    """对外暴露的秒数格式化"""
    return _seconds_to_text(seconds)
