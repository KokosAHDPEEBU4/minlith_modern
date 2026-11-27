"""Представление маршрута веток (``branch_path``) для GUI/отчётов/CLI.

Чистый модуль без Qt: принимает словарь ``{"labels": [...], "decisions": [...]}``
(как отдаёт ``AlgorithmOutput.path`` / ``ExcelRun.path.to_dict()``) и превращает
его в удобные строки/текст. Используется диалогом «Маршрут веток» и может
применяться в отчётах и CLI.
"""

from __future__ import annotations

import json

STAGE_TITLES: dict[str, str] = {
    "stage0": "Стадия 0",
    "type": "Тип породы",
    "stage_vi": "Этап VI",
}

_HEADERS = ("Стадия", "Ветка", "Условие", "Источник")


def describe_branch_path(path: dict | None) -> list[dict]:
    """Список строк маршрута: {stage, stage_title, name, condition, source}."""
    if not path:
        return []
    rows: list[dict] = []
    for d in path.get("decisions", []):
        stage = d.get("stage", "")
        rows.append({
            "stage": stage,
            "stage_title": STAGE_TITLES.get(stage, stage),
            "name": d.get("name", ""),
            "condition": d.get("condition", ""),
            "source": d.get("source", ""),
        })
    return rows


def branch_path_headers() -> tuple[str, ...]:
    """Заголовки колонок для табличного представления."""
    return _HEADERS


def _normalize_label(name: str) -> str:
    """'band_H5' -> 'H5', 'rock_type_3' -> '3', иначе без изменений."""
    if name.startswith("band_"):
        return name[len("band_"):]
    if name.startswith("rock_type_"):
        return name[len("rock_type_"):]
    return name


def path_branch_ids(path: dict | None) -> set[str]:
    """Множество id веток, пройденных образцом (для подсветки дерева)."""
    ids: set[str] = set()
    for decision in (path or {}).get("decisions", []):
        ids.add(_normalize_label(decision.get("name", "")))
    return ids


def forced_branch_ids(path: dict | None) -> set[str]:
    """Множество id веток, выбранных пользователем (``forced``)."""
    ids: set[str] = set()
    for decision in (path or {}).get("decisions", []):
        if decision.get("forced"):
            ids.add(_normalize_label(decision.get("name", "")))
    return ids


def branch_path_json(path: dict | None) -> str:
    """Маршрут в виде JSON-строки (для экспорта/сохранения)."""
    return json.dumps(path or {"labels": [], "decisions": []},
                      ensure_ascii=False, indent=2)


def _decision_pairs(path: dict | None) -> list[tuple[str, str]]:
    return [(d.get("stage", ""), d.get("name", ""))
            for d in (path or {}).get("decisions", [])]


def diff_branch_paths(path_a: dict | None, path_b: dict | None) -> list[dict]:
    """Различия двух маршрутов: ветки, присутствующие только в одном.

    Возвращает список ``{"stage", "name", "present_in"}``, где ``present_in``
    — ``"a"`` или ``"b"``.
    """
    pairs_a = _decision_pairs(path_a)
    pairs_b = _decision_pairs(path_b)
    diff: list[dict] = []
    for stage, name in pairs_a:
        if (stage, name) not in pairs_b:
            diff.append({"stage": stage, "name": name, "present_in": "a"})
    for stage, name in pairs_b:
        if (stage, name) not in pairs_a:
            diff.append({"stage": stage, "name": name, "present_in": "b"})
    return diff


def format_branch_path_text(path: dict | None, sample: str = "") -> str:
    """Человекочитаемый текст маршрута (для копирования/отчёта)."""
    rows = describe_branch_path(path)
    lines = [f"Маршрут веток{f': {sample}' if sample else ''}"]
    if not rows:
        lines.append("(путь не передан — движок его не отдаёт)")
        return "\n".join(lines)
    for r in rows:
        extra = []
        if r["condition"]:
            extra.append(r["condition"])
        if r["source"]:
            extra.append(f"[{r['source']}]")
        suffix = (" — " + " ".join(extra)) if extra else ""
        lines.append(f"  {r['stage_title']}: {r['name']}{suffix}")
    return "\n".join(lines)
