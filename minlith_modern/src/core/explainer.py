"""Explainer — generates human-readable explanations of the calculation process."""

from __future__ import annotations

import logging
from typing import Optional

from src.core.models import (
    CalculationResult,
    RockType,
)

logger = logging.getLogger(__name__)

# Rock type descriptions
_ROCK_TYPE_NAMES = {
    RockType.TYPE_1: "Type 1 (кварцдоминантные породы)",
    RockType.TYPE_2: "Type 2 (过渡ные к глинистым породам)",
    RockType.TYPE_3: "Type 3 (глинистые породы)",
    RockType.TYPE_4: "Type 4 (过渡ные к основным породам)",
    RockType.TYPE_5: "Type 5 (основные породы)",
}

_ROCK_TYPE_DESCRIPTIONS = {
    RockType.TYPE_1: (
        "Al₂O₃ ≤ 1.2Na₂O + K₂O. Порода бедна алюминием, "
        "полевые шпаты полностью распределены, остаток идёт в кварц."
    ),
    RockType.TYPE_2: (
        "Al₂O₃ ≤ 1.2Na₂O + 3.25K₂O. Умеренное содержание алюминия, "
        "возможна часть иллита."
    ),
    RockType.TYPE_3: (
        "Al₂O₃ ≤ 1.2Na₂O + 3.25K₂O + (MgO-0.5K₂O·k3)/k1. "
        "Глинистые породы с хлоритом."
    ),
    RockType.TYPE_4: (
        "Al₂O₃ ≤ 5Na₂O + 3.25K₂O + (MgO-0.5K₂O-2Na₂O)·k3/k1. "
        "过渡ные к основным породам."
    ),
    RockType.TYPE_5: (
        "Al₂O₃ превышает все пороги. Основные породы с преобладанием хлорита."
    ),
}

# Mineral explanations
_MINERAL_EXPLANATIONS = {
    "ab": "Альбит (NaAlSi₃O₈) — натриевый полевой шпат",
    "an": "Анортит (CaAl₂Si₂O₈) — кальциевый полевой шпат",
    "or_": "Ортоклаз (KAlSi₃O₈) — калиевый полевой шпат",
    "q": "Кварц (SiO₂) — свободный кремнезём",
    "ill": "Иллит — глинистый минерал (калиевая слюда)",
    "chl": "Хлорит — глинистый минерал (Mg,Fe,Al слюда)",
    "kn": "Каолинит (Al₂Si₂O₅(OH)₄) — глинистый минерал",
    "mm": "Монтмориллонит — глинистый минерал",
    "gb": "Гиббсит (Al(OH)₃) — гидроксид алюминия",
    "ap": "Апатит (Ca₅(PO₄)₃(F,Cl,OH)) — фосфат кальция",
    "cc": "Кальцит (CaCO₃) — карбонат кальция",
    "dl": "Доломит (CaMg(CO₃)₂) — карбонат кальция и магния",
}


class Explainer:
    """Generate human-readable explanations of the calculation process."""

    def __init__(self, language: str = "ru", detail_level: str = "standard") -> None:
        self._language = language
        self._detail_level = detail_level  # "brief", "standard", "detailed"

    def explain(self, result: CalculationResult) -> str:
        """Generate a full explanation for a calculation result."""
        sections = []

        # Header
        sections.append(f"Образец: {result.sample_name}")
        sections.append("")

        # Rock type
        rt = result.rock_type
        sections.append(f"Тип породы: {_ROCK_TYPE_NAMES.get(rt, rt.name)}")
        if self._detail_level != "brief":
            sections.append(_ROCK_TYPE_DESCRIPTIONS.get(rt, ""))
        sections.append("")

        # Coefficients
        coeff = result.coefficients
        sections.append("Адаптивные коэффициенты хлорита:")
        sections.append(f"  F = {coeff.F:.3f} — доля Fe³⁺/ΣFe = {coeff.F*100:.1f}%")
        sections.append(f"  A = {coeff.A:.3f} — доля Al/(Al+Fe)")
        sections.append(f"  k1 = {coeff.k1:.3f} — доля Mg, идущая в хлорит")
        sections.append(f"  k2 = {coeff.k2:.3f} — доля Fe²⁺ в хлорите")
        sections.append(f"  k3 = {coeff.k3:.3f} — доля Al в хлорите")
        sections.append(f"  k4 = {coeff.k4:.3f} — доля Si в хлорите")
        sections.append("")

        # Key calculation steps
        if self._detail_level != "brief":
            sections.append("Ключевые шаги расчёта:")
            sections.append("  1. Переведено в формульные единицы (ф.е.)")
            sections.append("  2. Вычтен апатит (P₂O₅ → CaO, F)")
            if result.input_composition.f > 0:
                sections.append("  3. Вычтен флюорит (F)")
            if result.input_composition.cl > 0:
                sections.append("  4. Вычтен галит (Cl)")
            sections.append(f"  5. Определён тип породы: {rt.name}")
            sections.append("  6. Распределены полевые шпаты (Ab, An, Or)")
            sections.append("  7. Рассчитаны глинистые минералы по адаптивным коэффициентам")
            sections.append("  8. Рассчитаны аксессуарные минералы (апатит, пирит и др.)")
            sections.append("  9. Переведено в весовые проценты")
            sections.append("  10. Нормализовано до 100%")
        sections.append("")

        # Dominant minerals
        minerals = result.minerals_weight
        mineral_list = [
            ("Ab", minerals.ab), ("An", minerals.an), ("Or", minerals.or_),
            ("Q", minerals.q), ("Ill", minerals.ill), ("Chl", minerals.chl),
            ("Kn", minerals.kn), ("Mm", minerals.mm), ("Gb", minerals.gb),
        ]
        nonzero = [(name, val) for name, val in mineral_list if val > 0.1]
        nonzero.sort(key=lambda x: -x[1])

        if nonzero:
            sections.append("Доминирующие минералы:")
            for name, val in nonzero[:5]:
                sections.append(f"  {name:5s} = {val:6.2f}%")
        sections.append("")

        # Anomalies
        if result.anomalies:
            sections.append("Обнаруженные аномалии:")
            for a in result.anomalies:
                icon = {"critical": "!!!", "warning": "!!", "info": "!"}[a.severity]
                sections.append(f"  [{icon}] {a.message}")
            sections.append("")

        # Defect summary
        if result.defect:
            max_defect_oxide = max(result.defect, key=lambda k: abs(result.defect[k]))
            max_defect_val = result.defect[max_defect_oxide]
            if abs(max_defect_val) > 0.5:
                sections.append(f"Макс. дефект: Δ{max_defect_oxide} = {max_defect_val:.2f} ф.е.")

        return "\n".join(sections)

    def explain_step(self, step: int, result: CalculationResult) -> str:
        """Explain a specific calculation step."""
        steps = {
            0: "Подготовка: конвертация вес.% в формульные единицы, коррекция CaO/F/Na.",
            1: "Определение F = Fe³⁺/ΣFe и A = Al/(Al+Fe).",
            2: "Расчёт адаптивных коэффициентов k1-k4 по 5 диапазонам F.",
            3: "Классификация типа породы (1-5) по соотношению Al-Na-K-Mg.",
            4: "Распределение полевых шпатов: Ab (Na), An (Ca), Or (K).",
            5: "Расчёт глинистых минералов: иллит, хлорит, каолинит.",
            6: "Расчёт аксессуарных минералов: апатит, пирит, карбонаты.",
            7: "Конвертация формульных единиц в весовые проценты.",
            8: "Нормализация до 100%.",
            9: "Расчёт дефекта (остатков оксидов).",
        }
        return steps.get(step, f"Шаг {step}: нет описания.")
