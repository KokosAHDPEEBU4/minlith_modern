"""Stage 3 — остаточные минералы: карбонаты, оксиды, свободный кварц.

Теория, файл 03.

Порядок: карбонаты (Dl → Cc → Sd) → рутил → гематит → магнетит →
родохрозит → кварц.

Ключевые отличия от VBA-порта:
- MnO → родохрозит (не пиролюзит)
- Fe₂O₃ → гематит (весь остаток)
- Убрано эмпирическое условие Ca_n < 250

Эта функция мутирует пулы `fe` на месте (вычитает израсходованное),
чтобы вызывающий код мог получить остаточные пулы (defect).
"""

from __future__ import annotations

from src.core.debug_tracer import DebugTraceCollector


def stage3(
    fe: dict[str, float],
    minerals: dict[str, float],
    tracer: DebugTraceCollector | None = None,
) -> dict[str, float]:
    """Стадия 3: карбонаты → оксиды → кварц.

    Args:
        fe: остаточные пулы (моли) после стадии 2 (мутируется на месте).
        minerals: уже распределённые минералы (мутируется на месте).

    Returns:
        Обновлённый словарь минералов.
    """
    ca = fe["cao"]
    mg = fe["mgo"]
    feo = fe["feo"]
    fe2o3 = fe.get("fe2o3", 0.0)
    co2 = fe["co2"]
    ti = fe["tio2"]
    mn = fe["mno"]
    si = fe["sio2"]

    # 1. Карбонаты (по CO2): доломит → кальцит → сидерит
    dl = min(ca, mg, co2 / 2.0)
    minerals["dl"] = dl
    ca -= dl
    mg -= dl
    co2 -= 2 * dl
    if tracer:
        tracer.record("Stage3", "Dl", dl, "Dl = min(Ca, Mg, CO2/2)")

    cc = min(ca, co2)
    minerals["cc"] = cc
    ca -= cc
    co2 -= cc
    if tracer:
        tracer.record("Stage3", "Cc", cc, "Cc = min(Ca, CO2)")

    sd = min(feo, co2)
    minerals["sd"] = sd
    feo -= sd
    co2 -= sd
    if tracer:
        tracer.record("Stage3", "Sd", sd, "Sd = min(FeO, CO2)")

    # 2. Рутил: n(Rt) = TiO2
    minerals["rt"] = ti
    ti = 0.0
    if tracer:
        tracer.record("Stage3", "Rt", minerals["rt"], "Rt = TiO2")

    # 3. Гематит: весь остаток Fe2O3
    minerals["ht"] = fe2o3
    fe2o3 = 0.0
    if tracer:
        tracer.record("Stage3", "Ht", minerals["ht"], "Ht = Fe2O3_ост")

    # 4. Магнетит: если остались и FeO, и Fe2O3
    mt = min(feo, fe2o3) if feo > 1e-9 and fe2o3 > 1e-9 else 0.0
    minerals["mt"] = mt
    feo -= mt
    if tracer:
        tracer.record("Stage3", "Mt", mt, "Mt = min(FeO, Fe2O3)")

    # 5. Родохрозит: n(Rch) = MnO
    minerals["rch"] = mn
    mn = 0.0
    if tracer:
        tracer.record("Stage3", "Rch", minerals["rch"], "Rch = MnO")

    # 6. Кварц: весь остаток SiO2 (финальный шаг)
    minerals["qz"] = max(si, 0.0)
    si = max(si, 0.0)
    if tracer:
        tracer.record("Stage3", "Qz", minerals["qz"], "Qz = SiO2_ост")

    # Записываем остатки обратно в пулы
    fe.update(
        cao=max(ca, 0.0), mgo=max(mg, 0.0), feo=max(feo, 0.0),
        fe2o3=max(fe2o3, 0.0), co2=max(co2, 0.0),
        tio2=ti, mno=mn, sio2=si,
    )
    return minerals
