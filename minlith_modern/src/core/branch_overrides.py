"""Ручной выбор веток (override) для движка ``excel_parity``.

Позволяет пользователю задать ветку решения вручную вместо автоматического
выбора. Объект пуст по умолчанию и **не меняет поведение**, пока не задан.

Валидация сверяется с каталогом решений ``branch_catalog`` (этап 1 ТЗ):
недопустимое решение/ветка или решение с ``overridable=False`` → ``ValueError``.

См. ``docs/planning/TZ_BRANCH_GRAPH.md`` (этап 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.excel_parity.branch_catalog import DECISIONS, branch_ids


@dataclass(frozen=True)
class BranchOverrides:
    """Выбор веток пользователем.

    ``choices``     — ``{decision_id: branch_id}`` (стадии 0/VI и др.);
    ``forced_path`` — упорядоченный список подписей веток (этап 6, внутренние
                      решения типов); пока не используется движком.
    """

    choices: dict[str, str] = field(default_factory=dict)
    forced_path: tuple[str, ...] = ()

    def get(self, decision_id: str) -> str | None:
        """Выбранная ветка решения или ``None`` (авто)."""
        return self.choices.get(decision_id)

    def is_empty(self) -> bool:
        return not self.choices and not self.forced_path

    def to_dict(self) -> dict:
        return {"choices": dict(self.choices), "forced_path": list(self.forced_path)}


def validate_overrides(overrides: BranchOverrides | None) -> None:
    """Проверить выбор по каталогу; при ошибке — ``ValueError``.

    ``None`` и пустой выбор допустимы (означают «как обычно»).
    """
    if overrides is None:
        return
    for decision_id, branch_id in overrides.choices.items():
        spec = DECISIONS.get(decision_id)
        if spec is None:
            raise ValueError(
                f"Неизвестное решение {decision_id!r}; доступны: {sorted(DECISIONS)}"
            )
        if not spec.overridable:
            raise ValueError(
                f"Решение {decision_id!r} не поддерживает ручной выбор "
                f"(overridable=False)"
            )
        allowed = branch_ids(decision_id)
        if branch_id not in allowed:
            raise ValueError(
                f"Недопустимая ветка {branch_id!r} для {decision_id!r}; "
                f"доступны: {list(allowed)}"
            )
