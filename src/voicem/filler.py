"""Очистка расшифровки: убираем слова-паразиты, заикания и мусор."""
from __future__ import annotations

import re

# Слова-паразиты (русский)
RU_FILLERS = [
    "э", "ээ", "эээ", "а-а", "ааа", "аа", "ммм", "мм", "м-м", "эм", "хм",
    "ну", "ну вот", "вот", "как бы", "типа", "типо", "короче", "в общем",
    "в принципе", "собственно", "значит", "так сказать", "это самое",
    "понимаешь", "понимаете", "как сказать", "в смысле", "скажем так",
    "блин", "ей богу", "на самом деле", "как-то так", "допустим",
    "честно говоря", "собственно говоря", "грубо говоря", "походу",
    "ну как бы", "ну типа", "ну вообще", "так вот", "вобщем",
]

# Слова-паразиты (английский)
EN_FILLERS = [
    "uh", "uhh", "um", "umm", "erm", "er", "ah", "ahh", "hmm", "mmm",
    "like", "you know", "i mean", "sort of", "kind of", "basically",
    "actually", "literally", "well", "so yeah", "right",
]

FILLERS = sorted(set(RU_FILLERS + EN_FILLERS), key=len, reverse=True)

_WORD_CHARS = r"[^\W\d_]"


def _filler_pattern() -> re.Pattern[str]:
    parts = [re.escape(f).replace(r"\ ", r"\s+") for f in FILLERS]
    return re.compile(
        r"(?<!%s)(?:%s)(?!%s)" % (_WORD_CHARS, "|".join(parts), _WORD_CHARS),
        re.IGNORECASE | re.UNICODE,
    )


FILLER_RE = _filler_pattern()

# Артефакты моделей Whisper (титры, реклама, тишина)
HALLUCINATIONS = [
    r"субтитры\s+(?:делал|подготовил|сделал)[^.!?\n]*",
    r"продолжение\s+следует\.{0,3}",
    r"редактор\s+субтитров[^.!?\n]*",
    r"subs?\s*by[^.!?\n]*",
    r"thanks?\s+for\s+watching[^.!?\n]*",
    r"\[?(?:музыка|аплодисменты|смех|music|applause|silence|blank_audio)\]?",
]


def _drop_hallucinations(text: str) -> str:
    for pattern in HALLUCINATIONS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def _collapse_repeats(text: str) -> str:
    """«я я я думаю» -> «я думаю», «так-так-так» -> «так»."""
    text = re.sub(r"\b(\w+)(?:[\s,]+\1\b)+", r"\1", text, flags=re.IGNORECASE | re.UNICODE)
    text = re.sub(r"\b(\w+)(?:-\1\b)+", r"\1", text, flags=re.IGNORECASE | re.UNICODE)
    return text


def _fix_spacing(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:%）)\]])", r"\1", text)
    text = re.sub(r"([(\[（])\s+", r"\1", text)
    text = re.sub(r"([,.!?;:])(?=[^\s\d.,!?])", r"\1 ", text)
    text = re.sub(r"\s*([,.!?;:])\s*\1+", r"\1", text)
    text = re.sub(r"^[\s,.;:!?-]+", "", text)
    return text.strip()


def _capitalize(text: str) -> str:
    def upper(match: re.Match[str]) -> str:
        return match.group(0).upper()

    text = re.sub(r"(?:^|(?<=[.!?]\s))([^\W\d_])", upper, text, flags=re.UNICODE)
    return text


def clean_text(text: str, remove_fillers: bool = True, punctuation: bool = True) -> str:
    """Приводит распознанный текст к чистому и понятному виду."""
    if not text:
        return ""

    result = _drop_hallucinations(text.strip())

    if remove_fillers:
        result = FILLER_RE.sub(" ", result)
        result = _collapse_repeats(result)

    result = _fix_spacing(result)

    if punctuation and result:
        result = _capitalize(result)
        if result[-1] not in ".!?…":
            result += "."

    return result
