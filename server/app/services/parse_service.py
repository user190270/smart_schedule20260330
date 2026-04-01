from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import json
import re
from threading import Lock
from uuid import uuid4

from pydantic import BaseModel

from app.models.enums import ScheduleSource
from app.schemas import (
    ParseAgentMessage,
    ParseAgentToolCall,
    ParseDraftRequest,
    ParseDraftResponse,
    ParseFollowUpQuestion,
    ParseSessionCreateRequest,
    ParseSessionDraftPatchRequest,
    ParseSessionMessageRequest,
    ParseSessionResponse,
    ScheduleDraft,
)
from app.services.ai_runtime import AiRuntimeError, AiRuntimeUnavailable, LangChainAiRuntime


KNOWN_TITLE_KEYWORDS: list[tuple[str, str]] = [
    ("吃饭", "吃饭"),
    ("开会", "开会"),
    ("上课", "上课"),
    ("面试", "面试"),
    ("讨论", "讨论"),
    ("复盘", "复盘"),
    ("汇报", "汇报"),
    ("见面", "见面"),
    ("学习", "学习"),
    ("训练", "训练"),
    ("演示", "演示"),
    ("答辩", "答辩"),
]
WEEKDAY_INDEX = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
}
TIME_RANGE_PATTERN = re.compile(
    r"(?P<start_hour>\d{1,2})"
    r"(?:(?:[:：](?P<start_minute>\d{1,2}))|(?P<start_half>半))?"
    r"(?:点|时)?"
    r"\s*(?:到|至|\-|~)\s*"
    r"(?P<end_hour>\d{1,2})"
    r"(?:(?:[:：](?P<end_minute>\d{1,2}))|(?P<end_half>半))?"
    r"(?:点|时)?"
)
TIME_POINT_PATTERN = re.compile(
    r"(?P<hour>\d{1,2})"
    r"(?:(?:[:：](?P<minute>\d{1,2}))|(?P<half>半))?"
    r"(?:点|时)"
)
ISO_DATETIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?")
END_ONLY_PATTERN = re.compile(
    r"(?:到|至|结束|结束于|结束在)\s*"
    r"(?P<hour>\d{1,2})"
    r"(?:(?:[:：](?P<minute>\d{1,2}))|(?P<half>半))?"
    r"(?:点|时)"
)
WEEKDAY_PATTERN = re.compile(r"(?:(下周|这周|周|星期))([一二三四五六日天])")
LOCATION_PATTERNS = [
    re.compile(
        r"(?:在|到)\s*(?P<location>[A-Za-z0-9\u4e00-\u9fff#\-\(\)·\.]{1,40}?)"
        r"(?=(?:吃饭|开会|上课|讨论|见面|汇报|面试|学习|复盘|训练|演示|答辩|$|，|。|,))"
    ),
    re.compile(r"(?:在|到)\s*(?P<location>[A-Za-z0-9#\-\(\)·\.]{1,40})"),
    re.compile(r"\bin\s+(?P<location>[A-Za-z][A-Za-z0-9#\-\(\)\. ]{1,40}?)(?=(?:$|[,.]))", re.IGNORECASE),
]
DATE_WORD_PATTERN = re.compile(r"(今天|明天|后天|今早|明早|今晚|下午|上午|早上|中午|晚上|傍晚|下周[一二三四五六日天]|周[一二三四五六日天]|星期[一二三四五六日天])")
FILLER_PATTERN = re.compile(r"(帮我|安排|记得|需要|想要|请|一下|一个|把|去|在|到)")
LEADING_LOCATION_TIME_PATTERN = re.compile(
    r"^(?:(?:今天|明天|后天|今早|明早|今晚|明晚|早上|上午|中午|下午|晚上|傍晚)\s*)*"
    r"(?:(?:从)?\d{1,2}(?:(?:[:：]\d{1,2})|半)?(?:点|时)?(?:\s*(?:到|至|\-|~)\s*)?)+"
    r"(?:在|到)?\s*"
)
TIME_LIKE_LOCATION_PATTERN = re.compile(
    r"^(?:(?:今天|明天|后天|今早|明早|今晚|明晚|早上|上午|中午|下午|晚上|傍晚)\s*)*"
    r"(?:(?:从|到|至|于)\s*)*"
    r"\d{1,2}(?:(?:[:：]\d{1,2})|半)?(?:点|时)"
    r"(?:\s*(?:到|至|\-|~)\s*\d{1,2}(?:(?:[:：]\d{1,2})|半)?(?:点|时)?)?"
    r"(?:\s*(?:开始|结束))?$"
)
ABSOLUTE_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}月\d{1,2}日")
CALENDAR_DATE_PATTERN = re.compile(r"(今天|明天|后天|今早|明早|今晚|明晚|下周[一二三四五六日天]|周[一二三四五六日天]|星期[一二三四五六日天])")


@dataclass
class SessionMessage:
    id: str
    role: str
    content: str


@dataclass
class SessionToolCall:
    name: str
    summary: str


@dataclass
class ParseSessionState:
    session_id: str
    user_id: int
    draft: ScheduleDraft
    messages: list[SessionMessage] = field(default_factory=list)
    tool_calls: list[SessionToolCall] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    follow_up_questions: list[ParseFollowUpQuestion] = field(default_factory=list)
    ready_for_confirm: bool = False
    next_action: str = "ask_follow_up"
    latest_assistant_message: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())


def _aware_now() -> datetime:
    return datetime.now().astimezone()


def _resolve_reference_time(reference_time: datetime | None) -> datetime:
    if reference_time is None:
        return _aware_now()
    if reference_time.tzinfo is None:
        return reference_time.astimezone()
    return reference_time


def _parse_iso_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    normalized = raw.replace(" ", "T")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _build_time(hour: int, minute: int | None, has_half: bool, meridiem: str) -> time:
    resolved_hour = hour
    resolved_minute = 30 if has_half else minute if minute is not None else 0
    if meridiem in {"afternoon", "evening"} and 1 <= resolved_hour < 12:
        resolved_hour += 12
    elif meridiem == "midday":
        if resolved_hour == 0:
            resolved_hour = 12
        elif 1 <= resolved_hour < 11:
            resolved_hour += 12
    if resolved_hour == 24:
        resolved_hour = 0
    return time(hour=resolved_hour, minute=resolved_minute)


def _resolve_target_date(text: str, reference_time: datetime) -> date:
    if "后天" in text:
        return (reference_time + timedelta(days=2)).date()
    if any(token in text for token in ("明天", "明早", "明晚")):
        return (reference_time + timedelta(days=1)).date()
    if any(token in text for token in ("今天", "今早", "今晚")):
        return reference_time.date()

    weekday_match = WEEKDAY_PATTERN.search(text)
    if not weekday_match:
        return reference_time.date()

    prefix, weekday_token = weekday_match.groups()
    target_weekday = WEEKDAY_INDEX[weekday_token]
    current_weekday = reference_time.weekday()
    days_ahead = (target_weekday - current_weekday) % 7

    if prefix == "下周":
        days_ahead = days_ahead + 7 if days_ahead != 0 else 7
    elif days_ahead == 0:
        days_ahead = 7

    return (reference_time + timedelta(days=days_ahead)).date()


def _resolve_meridiem(text: str) -> str:
    if any(token in text for token in ("下午", "傍晚")):
        return "afternoon"
    if any(token in text for token in ("今晚", "晚上", "明晚")):
        return "evening"
    if "中午" in text:
        return "midday"
    if any(token in text for token in ("今早", "明早", "早上", "上午", "清晨")):
        return "morning"
    return "plain"


def _combine_datetime(target_date: date, target_time: time, reference_time: datetime) -> datetime:
    return datetime.combine(target_date, target_time).replace(tzinfo=reference_time.tzinfo)


def _extract_iso_datetimes(text: str) -> list[datetime]:
    values: list[datetime] = []
    for match in ISO_DATETIME_PATTERN.finditer(text):
        parsed = _parse_iso_datetime(match.group(0))
        if parsed is not None:
            values.append(parsed)
    return values


def _normalize_location_candidate(raw_location: str) -> str | None:
    location = raw_location.strip(" ,，。.")
    if not location:
        return None
    location = LEADING_LOCATION_TIME_PATTERN.sub("", location).strip(" ,，。.")
    location = re.sub(r"^(?:在|到|于)\s*", "", location).strip(" ,，。.")
    location = re.sub(r"\s*(?:开始|结束)$", "", location).strip(" ,，。.")
    if not location:
        return None
    if TIME_LIKE_LOCATION_PATTERN.fullmatch(location):
        return None
    if re.search(r"\d{1,2}(?:(?:[:：]\d{1,2})|半)?(?:点|时)", location):
        return None
    return location


def _extract_location(text: str) -> str | None:
    for pattern in LOCATION_PATTERNS:
        for match in pattern.finditer(text):
            location = _normalize_location_candidate(match.group("location"))
            if location:
                return location
    return None


def _extract_title(text: str, location: str | None) -> str | None:
    for keyword, label in KNOWN_TITLE_KEYWORDS:
        if keyword in text:
            return label

    cleaned = text
    if location:
        cleaned = cleaned.replace(f"在{location}", "")
        cleaned = cleaned.replace(f"到{location}", "")
    cleaned = TIME_RANGE_PATTERN.sub("", cleaned, count=1)
    cleaned = END_ONLY_PATTERN.sub("", cleaned, count=1)
    cleaned = TIME_POINT_PATTERN.sub("", cleaned, count=1)
    cleaned = DATE_WORD_PATTERN.sub("", cleaned)
    cleaned = FILLER_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,，。.")
    if not cleaned or len(cleaned) <= 1:
        return None
    return cleaned[:120]


def _has_explicit_time(text: str) -> bool:
    return bool(TIME_RANGE_PATTERN.search(text) or TIME_POINT_PATTERN.search(text) or END_ONLY_PATTERN.search(text))


def _extract_temporal_range(text: str, reference_time: datetime) -> tuple[datetime | None, datetime | None]:
    iso_datetimes = _extract_iso_datetimes(text)
    if len(iso_datetimes) >= 2:
        return iso_datetimes[0], iso_datetimes[1]
    if len(iso_datetimes) == 1:
        return iso_datetimes[0], None

    target_date = _resolve_target_date(text, reference_time)
    meridiem = _resolve_meridiem(text)

    range_match = TIME_RANGE_PATTERN.search(text)
    if range_match:
        start_time = _build_time(
            hour=int(range_match.group("start_hour")),
            minute=int(range_match.group("start_minute")) if range_match.group("start_minute") else None,
            has_half=range_match.group("start_half") is not None,
            meridiem=meridiem,
        )
        end_time = _build_time(
            hour=int(range_match.group("end_hour")),
            minute=int(range_match.group("end_minute")) if range_match.group("end_minute") else None,
            has_half=range_match.group("end_half") is not None,
            meridiem=meridiem,
        )
        start = _combine_datetime(target_date, start_time, reference_time)
        end = _combine_datetime(target_date, end_time, reference_time)
        if end < start:
            end += timedelta(days=1)
        return start, end

    point_match = TIME_POINT_PATTERN.search(text)
    if point_match:
        start_time = _build_time(
            hour=int(point_match.group("hour")),
            minute=int(point_match.group("minute")) if point_match.group("minute") else None,
            has_half=point_match.group("half") is not None,
            meridiem=meridiem,
        )
        return _combine_datetime(target_date, start_time, reference_time), None

    return None, None


def _has_explicit_date_signal(text: str) -> bool:
    return bool(
        ISO_DATETIME_PATTERN.search(text)
        or ABSOLUTE_DATE_PATTERN.search(text)
        or CALENDAR_DATE_PATTERN.search(text)
        or WEEKDAY_PATTERN.search(text)
    )


def _replace_datetime_date(value: datetime, target_date: date) -> datetime:
    return datetime.combine(target_date, value.timetz())


def _resolve_session_anchor_date(
    current_draft: ScheduleDraft | None,
    latest_message: str,
    reference_time: datetime,
) -> date | None:
    if current_draft is None or _has_explicit_date_signal(latest_message):
        return None
    if current_draft.start_time is not None:
        return current_draft.start_time.date()
    if current_draft.remark and _has_explicit_date_signal(current_draft.remark):
        iso_datetimes = _extract_iso_datetimes(current_draft.remark)
        if iso_datetimes:
            return iso_datetimes[0].date()
        return _resolve_target_date(current_draft.remark, reference_time)
    return None


def _extract_follow_up_end_time(text: str, base_start_time: datetime | None, reference_time: datetime) -> datetime | None:
    if base_start_time is None:
        return None
    match = END_ONLY_PATTERN.search(text)
    if not match:
        return None
    meridiem = _resolve_meridiem(text)
    target_date = _resolve_target_date(text, reference_time)
    end_time = _build_time(
        hour=int(match.group("hour")),
        minute=int(match.group("minute")) if match.group("minute") else None,
        has_half=match.group("half") is not None,
        meridiem=meridiem,
    )
    end = _combine_datetime(target_date, end_time, reference_time)
    if end < base_start_time:
        end += timedelta(days=1)
    return end


def _message_clears_end_time(text: str) -> bool:
    return any(token in text for token in ("不设结束时间", "没有结束时间", "结束时间不填", "不用结束时间", "先不填结束时间"))


def _looks_like_follow_up_only(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) <= 8:
        return True
    if _has_explicit_time(text):
        return True
    return bool(_extract_location(text))


def _build_fallback_draft(
    text: str,
    reference_time: datetime,
    current_draft: ScheduleDraft | None = None,
) -> ScheduleDraft:
    location = _extract_location(text)
    start_time, end_time = _extract_temporal_range(text, reference_time)
    anchor_date = _resolve_session_anchor_date(current_draft, text, reference_time)
    if anchor_date is not None:
        if start_time is not None:
            start_time = _replace_datetime_date(start_time, anchor_date)
        if end_time is not None:
            end_time = _replace_datetime_date(end_time, anchor_date)
    title = _extract_title(text, location)
    return ScheduleDraft(
        title=title,
        start_time=start_time,
        end_time=end_time,
        location=location,
        remark=text.strip() or None,
        source=ScheduleSource.AI_PARSED,
    )


def _merge_draft(base: ScheduleDraft, incoming: ScheduleDraft, latest_message: str) -> ScheduleDraft:
    merged = base.model_copy(deep=True)
    title_signal = not _looks_like_follow_up_only(latest_message)

    if incoming.title and (not merged.title or title_signal):
        merged.title = incoming.title
    if incoming.start_time is not None:
        merged.start_time = incoming.start_time
    if incoming.end_time is not None:
        merged.end_time = incoming.end_time
    if incoming.location:
        merged.location = incoming.location
    if incoming.remark:
        merged.remark = incoming.remark
    return merged


def _compose_session_remark(user_messages: list[str]) -> str | None:
    cleaned = [message.strip() for message in user_messages if message.strip()]
    if not cleaned:
        return None
    return "\n".join(cleaned)


def _build_missing_fields(draft: ScheduleDraft) -> list[str]:
    missing: list[str] = []
    if not draft.title:
        missing.append("title")
    if not draft.start_time:
        missing.append("start_time")
    return missing


def _build_follow_up_questions(missing_fields: list[str]) -> list[ParseFollowUpQuestion]:
    prompts = {
        "title": "我还不确定这件事的标题。你希望把它记成什么？",
        "start_time": "我还缺少开始时间。你希望它什么时候开始？",
    }
    return [
        ParseFollowUpQuestion(field=field, question=prompts.get(field, f"请补充 {field}。"))
        for field in missing_fields
    ]


def _draft_visible(draft: ScheduleDraft) -> bool:
    return any(
        value
        for value in (
            draft.title,
            draft.start_time,
            draft.end_time,
            draft.location,
            draft.remark,
        )
    )


def _build_assistant_message(draft: ScheduleDraft, missing_fields: list[str], follow_ups: list[ParseFollowUpQuestion]) -> str:
    fragments: list[str] = []
    recognized: list[str] = []

    if draft.title:
        recognized.append(f"标题“{draft.title}”")
    if draft.start_time:
        recognized.append(f"开始时间 {draft.start_time.strftime('%Y-%m-%d %H:%M')}")
    if draft.end_time:
        recognized.append(f"结束时间 {draft.end_time.strftime('%Y-%m-%d %H:%M')}")
    if draft.location:
        recognized.append(f"地点 {draft.location}")

    if recognized:
        fragments.append("我先整理出当前草稿：" + "；".join(recognized) + "。")
    else:
        fragments.append("我先接住这条需求了，不过还没有形成足够结构化的草稿。")

    if missing_fields and follow_ups:
        fragments.append("接下来我还想确认：" + " ".join(item.question for item in follow_ups))
    elif not draft.end_time and draft.start_time:
        fragments.append("结束时间还没有设置。如果你知道的话可以继续补充；不填也可以直接确认保存。")
    else:
        fragments.append("信息已经基本齐了，你可以继续补充，也可以直接确认草稿。")

    return "\n".join(fragments)


def _extract_json_object(raw_text: str) -> dict | None:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


class ParseLLMOutput(BaseModel):
    title: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    remark: str | None = None
    storage_strategy: str | None = None


class ParseService:
    _lock = Lock()
    _sessions: dict[str, ParseSessionState] = {}

    @staticmethod
    def _get_runtime() -> LangChainAiRuntime | None:
        try:
            return LangChainAiRuntime.from_settings()
        except AiRuntimeUnavailable:
            return None

    @staticmethod
    async def _build_draft_with_langchain(
        text: str,
        reference_time: datetime,
        current_draft: ScheduleDraft | None,
    ) -> ScheduleDraft:
        runtime = ParseService._get_runtime()
        if runtime is None:
            return ParseService._build_draft_with_fallback(text, reference_time, current_draft)

        base_draft = current_draft or ScheduleDraft(source=ScheduleSource.AI_PARSED)
        fallback = ParseService._build_draft_with_fallback(text, reference_time, current_draft)
        payload = {
            "reference_time": reference_time.isoformat(),
            "current_draft": base_draft.model_dump(mode="json"),
            "latest_user_message": text,
            "heuristic_fallback": fallback.model_dump(mode="json"),
            "allowed_storage_strategies": ["local_only", "sync_to_cloud", "sync_to_cloud_and_knowledge"],
        }
        system_prompt = (
            "You are the scheduling AI service for a Chinese-first calendar product. "
            "Update the current schedule draft using the latest user message. "
            "Return structured JSON only. "
            "Interpret relative time using reference_time. "
            "Preserve confirmed draft information when the latest message does not replace it. "
            "Do not fabricate a precise end_time if the user did not provide one."
        )
        try:
            parsed = await runtime.ainvoke_structured_output(
                system_prompt=system_prompt,
                human_payload=payload,
                output_model=ParseLLMOutput,
                temperature=0,
            )
        except AiRuntimeError:
            return fallback
        title = parsed.title.strip() if parsed.title else fallback.title
        location = parsed.location.strip() if parsed.location else fallback.location
        remark = parsed.remark.strip() if parsed.remark else fallback.remark
        storage_strategy = parsed.storage_strategy
        if storage_strategy not in {"local_only", "sync_to_cloud", "sync_to_cloud_and_knowledge", None}:
            storage_strategy = base_draft.storage_strategy

        start_time = _parse_iso_datetime(parsed.start_time) if parsed.start_time else fallback.start_time
        end_time = _parse_iso_datetime(parsed.end_time) if parsed.end_time else fallback.end_time
        if start_time and end_time and end_time < start_time:
            end_time = None

        return ScheduleDraft(
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            remark=remark,
            source=ScheduleSource.AI_PARSED,
            storage_strategy=storage_strategy,
        )

    @staticmethod
    def _build_draft_with_fallback(
        text: str,
        reference_time: datetime,
        current_draft: ScheduleDraft | None = None,
    ) -> ScheduleDraft:
        return _build_fallback_draft(text, reference_time, current_draft)

    @staticmethod
    async def build_schedule_draft(payload: ParseDraftRequest, user_id: int) -> ParseDraftResponse:
        _ = user_id
        reference_time = _resolve_reference_time(payload.reference_time)
        draft = await ParseService._build_draft_with_langchain(payload.text.strip(), reference_time, None)
        missing_fields = _build_missing_fields(draft)
        follow_up_questions = _build_follow_up_questions(missing_fields)
        return ParseDraftResponse(
            draft=draft,
            missing_fields=missing_fields,
            follow_up_questions=follow_up_questions,
            requires_human_review=True,
            can_persist_directly=False,
        )

    @staticmethod
    def build_follow_up_questions(missing_fields: list[str]) -> list[dict[str, str]]:
        return [item.model_dump(mode="json") for item in _build_follow_up_questions(missing_fields)]

    @staticmethod
    def _build_session_response(session: ParseSessionState) -> ParseSessionResponse:
        return ParseSessionResponse(
            parse_session_id=session.session_id,
            messages=[ParseAgentMessage(**message.__dict__) for message in session.messages],
            draft=session.draft,
            missing_fields=session.missing_fields,
            follow_up_questions=session.follow_up_questions,
            ready_for_confirm=session.ready_for_confirm,
            next_action=session.next_action,  # type: ignore[arg-type]
            tool_calls=[ParseAgentToolCall(**call.__dict__) for call in session.tool_calls],
            latest_assistant_message=session.latest_assistant_message,
            draft_visible=_draft_visible(session.draft),
        )

    @staticmethod
    def _new_session(user_id: int) -> ParseSessionState:
        return ParseSessionState(
            session_id=str(uuid4()),
            user_id=user_id,
            draft=ScheduleDraft(source=ScheduleSource.AI_PARSED),
        )

    @staticmethod
    def _append_message(session: ParseSessionState, role: str, content: str) -> None:
        session.messages.append(SessionMessage(id=str(uuid4()), role=role, content=content))
        session.updated_at = _aware_now()

    @staticmethod
    def _append_tool_call(session: ParseSessionState, name: str, summary: str) -> None:
        session.tool_calls.append(SessionToolCall(name=name, summary=summary))
        session.tool_calls = session.tool_calls[-12:]

    @staticmethod
    def _user_messages(session: ParseSessionState) -> list[str]:
        return [message.content for message in session.messages if message.role == "user"]

    @staticmethod
    def _recompute_session_status(session: ParseSessionState) -> None:
        session.missing_fields = _build_missing_fields(session.draft)
        session.follow_up_questions = _build_follow_up_questions(session.missing_fields)
        session.ready_for_confirm = len(session.missing_fields) == 0
        session.next_action = "finalize_draft" if session.ready_for_confirm else "ask_follow_up"
        session.draft.source = ScheduleSource.AI_PARSED
        session.draft.remark = _compose_session_remark(ParseService._user_messages(session))

    @staticmethod
    async def _apply_message_turn(session: ParseSessionState, latest_message: str, reference_time: datetime) -> None:
        current_draft = session.draft.model_copy(deep=True)
        parsed = await ParseService._build_draft_with_langchain(latest_message, reference_time, current_draft)
        merged = _merge_draft(current_draft, parsed, latest_message)

        if _message_clears_end_time(latest_message):
            merged.end_time = None
        else:
            follow_up_end_time = _extract_follow_up_end_time(latest_message, merged.start_time, reference_time)
            if follow_up_end_time is not None:
                merged.end_time = follow_up_end_time

        if current_draft.storage_strategy and not merged.storage_strategy:
            merged.storage_strategy = current_draft.storage_strategy

        session.draft = merged
        ParseService._recompute_session_status(session)
        ParseService._append_tool_call(session, "update_draft", "根据最新回复更新了当前日程草稿。")

        assistant_message = _build_assistant_message(session.draft, session.missing_fields, session.follow_up_questions)
        session.latest_assistant_message = assistant_message
        ParseService._append_message(session, "assistant", assistant_message)

        if session.ready_for_confirm:
            ParseService._append_tool_call(session, "finalize_draft", "当前草稿已经具备确认保存条件。")
        else:
            ParseService._append_tool_call(session, "ask_follow_up", "当前草稿仍有缺失字段，继续发起澄清。")

    @staticmethod
    async def create_session(payload: ParseSessionCreateRequest, user_id: int) -> ParseSessionResponse:
        reference_time = _resolve_reference_time(payload.reference_time)
        session = ParseService._new_session(user_id)
        ParseService._append_message(session, "user", payload.message.strip())
        await ParseService._apply_message_turn(session, payload.message.strip(), reference_time)
        with ParseService._lock:
            ParseService._sessions[session.session_id] = session
        return ParseService._build_session_response(session)

    @staticmethod
    def _require_session(session_id: str, user_id: int) -> ParseSessionState:
        with ParseService._lock:
            session = ParseService._sessions.get(session_id)
        if session is None or session.user_id != user_id:
            raise KeyError("parse session not found")
        return session

    @staticmethod
    async def append_session_message(
        session_id: str,
        payload: ParseSessionMessageRequest,
        user_id: int,
    ) -> ParseSessionResponse:
        reference_time = _resolve_reference_time(payload.reference_time)
        session = ParseService._require_session(session_id, user_id)
        ParseService._append_message(session, "user", payload.message.strip())
        await ParseService._apply_message_turn(session, payload.message.strip(), reference_time)
        return ParseService._build_session_response(session)

    @staticmethod
    async def patch_session_draft(
        session_id: str,
        payload: ParseSessionDraftPatchRequest,
        user_id: int,
    ) -> ParseSessionResponse:
        session = ParseService._require_session(session_id, user_id)
        patch = payload.draft.model_dump(exclude_unset=True)

        for field_name, value in patch.items():
            setattr(session.draft, field_name, value)

        ParseService._recompute_session_status(session)
        session.latest_assistant_message = None
        ParseService._append_tool_call(session, "update_draft", "已按用户手动编辑同步当前草稿。")
        return ParseService._build_session_response(session)
