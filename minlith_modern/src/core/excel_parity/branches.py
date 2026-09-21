"""Структурированная траектория ветвлений движка excel_parity.

Дополняет текстовые ``TypeSolution.trace`` / ``StageVI.trace`` и решения
стадии 0 (полоса коэффициентов, тип породы) единым ``BranchPath`` —
представлением уже принятых решений, пригодным для визуализации графа
разветвлений и выбора ветки пользователем.

Модуль **ничего не меняет в расчёте**: он только собирает в структуру те
ветки, которые движок и так выбирает. Добавлен для функционала «граф
разветвлений», см. docs/planning/BRANCH_GRAPH_SELECTION.md.

Идентификаторы веток:
  * стадия 0 — ``H5`` / ``J5`` / ``L5`` / ``H12`` / ``J12`` / ``L12``
    (полоса k1..k4/achl) и ``rock_type_1..5``;
  * тип — подписи из ``TypeSolution.trace`` (``t_67``, ``p_253``, ``m_274``…);
  * стадия VI — ``A``, ``B``, ``C-srp``, ``C-mst``, ``C-mst2``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class BranchDecision:
    """Одно принятое решение о ветке."""

    stage: str                 # "stage0" | "type" | "stage_vi"
    name: str                  # идентификатор ветки
    condition: str = ""        # человекочитаемое условие (если известно)
    source: str = ""           # источник в Excel (ячейка/флаг/процедура)
    value: float | None = None  # значение условия/переменной, если применимо


@dataclass
class BranchPath:
    """Последовательность принятых решений (маршрут образца)."""

    decisions: list[BranchDecision] = field(default_factory=list)

    def add(
        self,
        stage: str,
        name: str,
        condition: str = "",
        source: str = "",
        value: float | None = None,
    ) -> None:
        self.decisions.append(
            BranchDecision(stage=stage, name=name, condition=condition,
                           source=source, value=value)
        )

    def labels(self) -> list[str]:
        return [d.name for d in self.decisions]

    def by_stage(self, stage: str) -> list[BranchDecision]:
        return [d for d in self.decisions if d.stage == stage]

    def to_dict(self) -> dict:
        return {
            "labels": self.labels(),
            "decisions": [asdict(d) for d in self.decisions],
        }


# Полоса коэффициентов k1..k4/achl -> (условие, Excel-флаг каскада u_0..u_10).
COEFFICIENT_BAND_INFO: dict[str, tuple[str, str]] = {
    "H5": ("0 < F < 0.21", "G17"),
    "J5": ("0.21 <= F < 0.51", "H17"),
    "L5": ("0.51 <= F < 0.69", "I17"),
    "H12": ("0.69 <= F < 0.87 и A > 0.47", "J17"),
    "J12": ("0.69 <= F < 0.87 и 0.40 < A < 0.47", "G18"),
    "L12": ("иначе (0.87 <= F < 1.0)", "I18"),
}

# Тип породы -> (условие, Excel-флаг листа «Нач+Type 3»).
ROCK_TYPE_INFO: dict[int, tuple[str, str]] = {
    1: ("Al - Na - K < 0 или Al - (1.2Na+K) <= 0", "F20/F21"),
    2: ("Al - (1.2Na + 3.25K) <= 0", "F22"),
    3: ("Al <= 1.2Na + 3.25K + (Mg-0.5K)*k3/k1", "F24"),
    4: ("Al <= 5Na + 3.25K + (Mg-0.5K-2Na)*k3/k1", "F25"),
    5: ("прочее (высокое Al)", "F26"),
}

# Ветка VI этапа -> (условие, VBA-процедура).
STAGE_VI_INFO: dict[str, tuple[str, str]] = {
    "A": ("ca_n >= mg_n + fe_n", "s_97t"),
    "B": ("mg_n <= ca_n < mg_n + fe_n", "s_104t/s_111"),
    "C-srp": ("ca_n < mg_n и si_n > 2/3*(mg_n-ca_n)", "s_125t"),
    "C-mst": ("ca_n < mg_n и si_n < mg_n-ca_n", "s_131"),
    "C-mst2": ("ca_n < mg_n, иначе", "s_137"),
}

# Подпись ветки типа -> (условие, источник). Условия заполняются по мере
# уточнения; для неизвестных подписей остаётся только идентификатор.
# Источник — VBA-процедура/блок листа «Нач+Type 3»/«Нач+Type 12».
TYPE_BRANCH_INFO: dict[str, tuple[str, str]] = {
    "t_52~53": ("an=al1, иначе an=0.2na (Si хватает)", "t_52/t_53"),
    "t_58": ("al1<=ca, не хватает SiO2 на анортит", "t_58"),
    "t_67": ("al1>ca и e46-2ca>=0", "t_67/t_68"),
    "t_83": ("al1>ca, не хватает Si по Ca (БК-1)", "t_83"),
    "ill-kz (D177-D179)": ("иллито-кварцевый коридор D177", "s_177/s_179"),
    "an=0.2na": ("анортит по лимиту Na", "D26"),
    "an=ca": ("анортит по Ca", "D68"),
    "an=0.2na(I)": ("анортит по Na, I-вариант", "D30"),
    "ill+or": ("иллит + ортоклаз", "D190"),
    "ill-gb (D274)": ("иллит-гиббсит (D274)", "D274"),
    "fe-ill": ("иллит по Fe", "s_208"),
    "fe-ill-mg": ("иллит по Mg", "s_213"),
    "p_53t": ("плагиоклаз-зона p_53", "p_53"),
    "D61": ("an=0.2na", "D61"),
    "D68": ("an=ca", "D68"),
    "p_142": ("ill=mg", "p_142"),
    "D106": ("rVI-путь", "D106"),
    "F119+": ("хлорит по Al", "F119"),
    "F126-": ("хлорит по Mg", "F126"),
    "3331": ("тип 3, ветка 3331", "p_163"),
    "3332a": ("тип 3, 3332a (chl по Al)", "p_180"),
    "3332b": ("тип 3, 3332b (chl по Fe)", "p_188"),
    "3333a": ("тип 3, 3333a", "p_199"),
    "3333b": ("тип 3, 3333b", "p_222"),
    "s_271": ("тип 3, s_271", "s_271"),
    "p253->t5": ("p_253 -> тип 5", "p_253"),
    "t5": ("тип 5", "aType_5"),
    "t45-aType5": ("тип 5 (aType_5)", "aType_5"),
    "t45-m504": ("тип 4/5, m_504", "m_504"),
    "t45-m513->t5": ("тип 4/5, m_513 -> t5", "m_513"),
    "t45-m552t->t5": ("тип 4/5, m_552t -> t5", "m_552"),
    "t45-m418t": ("тип 4/5, m_418t (Fe-путь)", "m_418"),
    "t45-m424->t5": ("тип 4/5, m_424 -> t5", "m_424"),
    "type45-normal": ("тип 4/5, обычный путь", "aType_4"),
}
