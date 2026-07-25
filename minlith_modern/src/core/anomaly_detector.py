"""Smart anomaly detector — analyzes defect and composition to find issues."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

from src.core.models import CalculationResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnomalyHypothesis:
    """Hypothesis about an anomaly in the calculation."""

    severity: Literal["info", "warning", "critical"]
    pattern: str
    message: str
    confidence: float  # 0.0 — 1.0
    suggested_action: str
    affected_oxides: list[str] = field(default_factory=list)


# Built-in detection rules
_RULES: list[tuple[str, callable, float, str, str]] = []


def _rule(name: str, severity: str, message: str, action: str, confidence: float = 0.8):
    """Decorator to register a detection rule."""
    def decorator(func):
        _RULES.append((name, func, confidence, message, action, severity))
        return func
    return decorator


@_rule("high_ca_so3", "warning",
       "CaO > 2% и SO₃ > 1%: возможно, присутствует гипс/ангидрит",
       "Проверьте исходные данные на наличие CaSO₄", 0.7)
def _check_gypsum(result: CalculationResult) -> tuple[bool, list[str]]:
    comp = result.input_composition
    return (comp.cao > 2.0 and comp.so3 > 1.0), ["cao", "so3"]


@_rule("low_sum", "info",
       "Сумма оксидов < 95%: возможна потеря летучих (LOI) или ошибка лаборатории",
       "Убедитесь, что LOI учтён в анализе", 0.6)
def _check_low_sum(result: CalculationResult) -> tuple[bool, list[str]]:
    total = result.input_composition.sum()
    return total < 95.0, []


@_rule("high_sum", "warning",
       "Сумма оксидов > 103%: ошибка нормализации или переучёт",
       "Проверьте корректность ввода данных", 0.8)
def _check_high_sum(result: CalculationResult) -> tuple[bool, list[str]]:
    total = result.input_composition.sum()
    return total > 103.0, []


@_rule("iron_rich", "info",
       "Fe₂O₃ + FeO > 25%: железистая порода, возможна ошибка в Fe³⁺/Fe²⁺",
       "Проверьте соотношение Fe³⁺/Fe²⁺", 0.5)
def _check_iron_rich(result: CalculationResult) -> tuple[bool, list[str]]:
    fe_total = result.input_composition.fe2o3 + result.input_composition.feo
    return fe_total > 25.0, ["fe2o3", "feo"]


@_rule("apatite_incomplete", "warning",
       "P₂O₅ > 2% при дефекте по CaO: апатит не полностью учтён",
       "Проверьте корректность расчёта апатита", 0.7)
def _check_apatite(result: CalculationResult) -> tuple[bool, list[str]]:
    comp = result.input_composition
    cao_defect = result.defect.get("cao", 0.0)
    return (comp.p2o5 > 2.0 and cao_defect > 0.5), ["p2o5", "cao"]


@_rule("critical_defect", "critical",
       "Дефект > 5% по одному оксиду: критическая проблема, требуется ручной анализ",
       "Проверьте исходные данные и алгоритм расчёта", 0.9)
def _check_critical_defect(result: CalculationResult) -> tuple[bool, list[str]]:
    if not result.defect:
        return False, []
    max_oxide = max(result.defect, key=lambda k: abs(result.defect[k]))
    max_defect = abs(result.defect[max_oxide])
    return max_defect > 5.0, [max_oxide]


@_rule("carbonate_incomplete", "info",
       "CO₂ > 5% при дефекте по CaO: карбонаты не полностью распределены",
       "Проверьте учёт карбонатов (кальцит, доломит)", 0.6)
def _check_carbonate(result: CalculationResult) -> tuple[bool, list[str]]:
    comp = result.input_composition
    cao_defect = result.defect.get("cao", 0.0)
    return (comp.co2 > 5.0 and cao_defect > 0.5), ["co2", "cao"]


@_rule("feldspar_anomaly", "info",
       "An > 10% при Type 1-2: необычное содержание анортита",
       "Проверьте содержание CaO и Al₂O₃", 0.5)
def _check_feldspar(result: CalculationResult) -> tuple[bool, list[str]]:
    return result.minerals_weight.an > 10.0, ["cao", "al2o3"]


@_rule("high_phosphorus", "warning",
       "P₂O₅ > 0.5%: повышенное содержание фосфора",
       "Убедитесь, что апатит корректно вычитается из CaO", 0.6)
def _check_phosphorus(result: CalculationResult) -> tuple[bool, list[str]]:
    return result.input_composition.p2o5 > 0.5, ["p2o5"]


@_rule("negative_mineral", "warning",
       "Отрицательное значение минерала: возможна ошибка в коэффициентах",
       "Проверьте коэффициенты k1-k4 и тип породы", 0.7)
def _check_negative_mineral(result: CalculationResult) -> tuple[bool, list[str]]:
    minerals = result.minerals_weight
    negative = []
    for field in ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb"]:
        val = getattr(minerals, field, 0.0)
        if val < -0.1:
            negative.append(field)
    return len(negative) > 0, negative


class AnomalyDetector:
    """Analyze calculation results for anomalies and provide hypotheses.

    Singleton: use AnomalyDetector.instance() to get the shared instance.
    """

    _instance: Optional["AnomalyDetector"] = None

    def __init__(self, rules_path: Optional[str] = None) -> None:
        self._rules = list(_RULES)
        logger.debug("AnomalyDetector initialized with %d rules", len(self._rules))

    @classmethod
    def instance(cls) -> "AnomalyDetector":
        """Get the shared singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def analyze(self, result: CalculationResult) -> list[AnomalyHypothesis]:
        """Analyze a single result for anomalies."""
        hypotheses = []
        for name, func, confidence, message, action, severity in self._rules:
            try:
                triggered, affected = func(result)
                if triggered:
                    hypotheses.append(AnomalyHypothesis(
                        severity=severity,
                        pattern=name,
                        message=message,
                        confidence=confidence,
                        suggested_action=action,
                        affected_oxides=affected,
                    ))
            except Exception as e:
                logger.warning("Rule %s failed: %s", name, e)
        return hypotheses

    def analyze_batch(
        self, results: list[CalculationResult]
    ) -> dict[str, list[AnomalyHypothesis]]:
        """Analyze multiple results, keyed by sample name."""
        return {r.sample_name: self.analyze(r) for r in results}
