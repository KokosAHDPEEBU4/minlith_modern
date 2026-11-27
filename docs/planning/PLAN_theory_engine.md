# План: Собственный расчётный движок на основе теории (00-07)

## Текущая архитектура

```
calculator.py  →  AlgorithmInput  →  RealAlgorithm.compute()  →  AlgorithmOutput
                       ↑                                            ↓
                  Stage 0                                   Stage VI → вес.% → нормировка
              (массы→моли,                                          → defect
               коррекция Ca/F/Na,
               k1-k4, тип породы)
```

**Проблема**: `RealAlgorithm` — это попытка портировать VBA макрос из Excel. Но VBA макрос нам недоступен, а реализация содержит расхождения с теорией (см. анализ выше).

## Новая архитектура

```
calculator.py  →  AlgorithmInput  →  TheoryAlgorithm.compute()  →  AlgorithmOutput
                       ↑                                            ↓
                  Stage 0                                   Stage VI → вес.% → нормировка
              (без изменений)                                    → defect
```

**Цель**: заменить `RealAlgorithm` на `TheoryAlgorithm`, написанный строго по теории из файлов 00-07. Старый `RealAlgorithm` переименовывается в `VbaPortStub` (заглушка для будущего порта макроса).

---

## Файлы для изменения

### Новые файлы
| Файл | Описание |
|------|----------|
| `src/core/theory_algorithm.py` | Новый движок по теории |
| `src/core/stage1.py` | Стадия 1: апатит, пирит, гипс, флюорит, галит |
| `src/core/stage2.py` | Стадия 2: полевые шпаты, глины, гиббсит + классификация |
| `src/core/stage3.py` | Стадия 3: карбонаты, оксиды, кварц |
| `tests/test_theory_algorithm.py` | Тесты на основе разобранных примеров из06 |

### Изменяемые файлы
| Файл | Изменение |
|------|-----------|
| `src/core/algorithm_real.py` | Переименовать класс → `VbaPortStub`, добавить deprecation warning |
| `src/core/calculator.py` | Переключить default на `TheoryAlgorithm` |
| `src/core/models.py` | Добавить поле `k_or` в `AdaptiveCoefficients` (для разделения K₂O) |
| `src/core/constants.py` | Добавить `MOLAR_MASSES` теоретические (сверить с таблицей 00) |

---

## Детали реализации

### 1. `stage1.py` — Второстепенные минералы (файл 01)

```python
def stage1(fe: dict[str, float]) -> tuple[dict[str, float], dict[str, float]]:
    """
    Стадия 1: Ap → Py → Gp → Fl → Hl
    
    Args:
        fe: исходные моли оксидов (после пересчёта из вес.%)
    
    Returns:
        (minerals, residuals) — минералы и остаточные пулы
    """
```

**Порядок шагов** (строго по теории):
1. **Апатит**: `n(Ap) = n(P2O5)`, расход `CaO = 3.33 * P2O5`
2. **Пирит**: `n(Py) = n(S) / 2`, расход `FeO = n(Py)`
3. **Гипс**: `n(Gp) = n(SO3)`, расход `CaO = n(SO3)`
4. **Флюорит**: `n(Fl) = n_ост(F) / 2`, расход `CaO = n(Fl)`
5. **Галит**: `n(Hl) = n(Cl) / 2`, расход `Na2O = n(Hl)`

**Ключевое отличие от текущей реализации**: F не корректируется через P₂O₅ ( теория: F и P₂O₅ — независимые элементы).

### 2. `stage2.py` — Алюмосодержащие минералы (файл 02)

```python
def classify_rock_type(al: float, na: float, k: float, ca: float) -> int:
    """Классификация типа породы 1-5 по индикатору R."""

def stage2(fe: dict[str, float], rock_type: int, k_or: float) -> tuple[dict, dict]:
    """
    Стадия 2: Or → Ab → An → Ilt → Kln → Chl → Gbs
    
    k_or: доля K₂O, идущая в ортоклаз (0.0-1.0)
    """
```

**Порядок**:
1. **Ортоклаз**: `n(Or) = k_or * min(K2O, Al2O3)` — **НОВОЕ**: доля K через k_or
2. **Альбит**: `n(Ab) = min(Na2O, Al2O3_ост)`
3. **Анортит**: `n(An) = min(CaO, Al2O3_ост)`
4. **Иллит**: `n(Ilt) = min((1-k_or)*K2O / 2, Al2O3_ост / 3, SiO2_ост / 16)` — **НООЕ**: K от k_or
5. **Каолинит**: `n(Kln) = Al2O3_ост` (с проверкой SiO2)
6. **Хлорит**: `n(Chl) = min(MgO/k1, FeO/k2, Al2O3_ост/k3, SiO2_ост/k4)`
7. **Гиббсит**: `n(Gbs) = Al2O3_ост` (весь остаток)

**Ключевые отличия**:
- K₂O делится между Or и Ilt через k_or (instead of "first-come-first-served")
- k_or — параметр, зависит от типа породы (для аркозов ~0.4, для глин ~0.1)

### 3. `stage3.py` — Остаточные минералы (файл 03)

```python
def stage3(fe: dict[str, float], minerals: dict) -> dict[str, float]:
    """
    Стадия 3: карбонаты → оксиды → кварц
    
    Returns: обновлённые минералы
    """
```

**Порядок**:
1. **Карбонаты** (по CO₂):
   - Доломит: `n(Dl) = min(CaO_ост, MgO_ост, CO2_ост/2)`
   - Кальцит: `n(Cc) = min(CaO_ост, CO2_ост)`
   - Сидерит: `n(Sd) = min(FeO_ост, CO2_ост)`
2. **Рутил**: `n(Rt) = TiO2`
3. **Гематит**: `n(Ht) = Fe2O3_ост` (весь остаток Fe₂O₃) — **ИСПРАВЛЕНИЕ**: было `fe_n/2`
4. **Магнетит**: `n(Mt) = min(FeO_ост, Fe2O3_ост)` (если есть оба)
5. **Родохрозит**: `n(Rch) = MnO` — **ИСПРАВЛЕНИЕ**: было `prl = mn_n`
6. **Кварц**: `n(Qz) = SiO2_ост`

**Ключевые отличия**:
- MnO → Rhodochrosite (не Pyrolusite)
- Fe₂O₃ → Hematite (100% остатка, не 50%)
- Убрано условие `Ca_n < 250` (нет в теории)

### 4. `theory_algorithm.py` — Главный оркестратор

```python
class TheoryAlgorithm:
    """Расчётный движок строго по теории (файлы 00-07)."""
    
    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        # 1. Stage 1: второстепенные минералы
        minerals_s1, residuals = stage1(inp)
        
        # 2. Классификация типа породы
        rock_type = classify_rock_type(residuals)
        
        # 3. Stage 2: алюмосодержащие
        minerals_s2, residuals = stage2(residuals, rock_type, k_or=...)
        
        # 4. Stage 3: остаточные
        minerals_s3 = stage3(residuals, minerals_s2)
        
        # 5. Собрать всё в AlgorithmOutput
        return AlgorithmOutput(...)
```

### 5. Коэффициент k_or

Добавить в `AdaptiveCoefficients`:
```python
k_or: float  # доля K₂O в ортоклазе (0.0-1.0)
```

Значения k_or по типам пород (ТРЕБУЕТ КАЛИБРОВКИ):
| Тип | k_or | Обоснование |
|-----|------|-------------|
| 1 | 1.0 | Кварцевый песчаник — K идёт в полевой шпат |
| 2 | 0.7 | Аркоз — большая часть K в полевом шпате |
| 3 | 0.5 | Граувака — поровну |
| 4 | 0.2 | Глины — большая часть K в иллите |
| 5 | 0.1 | Латериты — почти весь K в иллите |

### 6. Тесты (файл06)

Добавить разобранный числовой пример как regression test:
```python
def test_worked_example_06():
    """Пример из файла 06: SiO2=52.5, Al2O3=23.41, ..."""
    sample = Sample(
        name="T-O2",
        composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45
        )
    )
    calc = Calculator(algorithm=TheoryAlgorithm())
    result = calc.calculate_single(sample)
    
    # Проверяем что баланс сходится
    assert result.defect["sio2"] >= 0  # кварц не отрицательный
    assert result.defect["feo"] >= 0   # FeO не перерасходован
    assert result.defect["mgo"] >= 0   # MgO не перерасходован
```

---

## Фаза 2: Валидация и robustness

### 10. Баланс массы
Проверять: `Σ минералов ≈ Σ оксидов + конституционная вода гидратов`
- Каолинит добавляет 2·H₂O (36.04 г/моль)
- Иллит добавляет 2·H₂O
- Хлорит добавляет 4·H₂O
- Гиббсит добавляет 3·H₂O
- Гипс добавляет 2·H₂O

### 11. LOI/H₂O проверка
- Если LOI измерен: `LOI ≥ Σ(вода гидратов) + CO₂(карбонатов)`
- Если LOI < требуемого: предупреждение "LOI не покрывает воду минералов"
- Если LOI отсутствует: пометка "расчёт без учёта LOI"

### 12. Fe₂O₃/FeO режим
`CalculationConfig.fe_split_mode`:
- `"auto"` — текущий (Fe₂O₃ × 0.9 + FeO)
- `"manual"` — пользователь задаёт коэффициент окисленности `fe3_ratio`

---

## Фаза 3: Расширение минерального набора

### 13. Заглушки недостающих минералов
Добавить в `AlgorithmOutput`:
```python
glt: float = 0.0   # Глауконит (TBD, файл 07)
bt: float = 0.0    # Биотит (TBD, файл 07)
srp_fe: float = 0.0  # Fe-Mg силикат (TBD, файл 07)
```
Пока не рассчитываются, но готовы к добавлению.

### 14. Калибратор k_or
Расширить `calibrator.py`:
```python
# Добавить k_or в пространство параметров
bounds = [
    (0.0, 1.0),   # k_or
    (0.5, 5.0),   # k1
    (0.5, 5.0),   # k2
    (0.5, 5.0),   # k3
    (0.5, 5.0),   # k4
]
```

---

## Фаза 4: Архитектурные улучшения

### 16. AlgorithmFactory
```python
class AlgorithmFactory:
    @staticmethod
    def create(mode: str = "theory") -> MineralAlgorithm:
        if mode == "theory":
            return TheoryAlgorithm()
        elif mode == "vba_port":
            return VbaPortStub()
        else:
            raise ValueError(f"Unknown mode: {mode}")
```

### 17. Step recorder
Вместо `DebugTraceCollector` (записывает "что") — `StepRecorder` (записывает "почему"):
```python
class StepRecorder:
    def record_step(self, stage: str, mineral: str, 
                    condition: str, value: float, reason: str):
        """Записывает шаг с объяснением условия."""
```

### 18. Сравнение theory vs VBA
```python
def compare_algorithms(sample: Sample) -> dict:
    """Запускает оба движка и выводит diff."""
    theory = TheoryAlgorithm().compute(inp)
    vba = VbaPortStub().compute(inp)
    return diff(theory, vba)
```

### 19. Векторизованный numpy batch
Для выборок >1000 проб:
```python
# Вместо:
for sample in samples:
    result = calculate(sample)

# Векторизованно:
oxides = np.array([s.composition.to_array() for s in samples])
results = vectorized_calculate(oxides)  # np.where, маски
```

---

## Фаза 5: Тестирование

### 20. Эталонные составы
```python
REFERENCE_ROCKS = {
    "quartz_sandstone": OxideComposition(sio2=95, al2o3=2, ...),
    "arkose": OxideComposition(sio2=70, al2o3=15, k2o=5, ...),
    "clay": OxideComposition(sio2=55, al2o3=25, ...),
    "limestone": OxideComposition(cao=50, co2=40, ...),
}
```

### 21. Граничные тесты
```python
def test_zero_calcium():     # CaO=0 → нет An, Cc, Dl
def test_zero_co2():         # CO2=0 → карбонаты по остатку CaO
def test_zero_alumina():     # Al2O3=0 → нет глинистых
def test_zero_potassium():   # K2O=0 → нет Or, Ilt
```

---

## Порядок реализации (все 21 шаг)

| # | Фаза | Что делаем | Сложность |
|---|------|-----------|-----------|
| 1 | Ядро | `stage1.py` — Ap → Py → Gp → Fl → Hl | Лёгкая |
| 2 | Ядро | `stage2.py` — Or → Ab → An → Ilt → Kln → Chl → Gbs + classify | Средняя |
| 3 | Ядро | `stage3.py` — Карбонаты → Оксиды → Qz | Лёгкая |
| 4 | Ядро | `theory_algorithm.py` — оркестратор | Лёгкая |
| 5 | Ядро | `k_or` в `AdaptiveCoefficients` + defaults по типам | Лёгкая |
| 6 | Ядро | Переключить `calculator.py` на TheoryAlgorithm | Лёгкая |
| 7 | Ядро | Переименовать `RealAlgorithm` → `VbaPortStub` | Лёгкая |
| 8 | Ядро | Тест из файла 06 | Средняя |
| 9 | Ядро | Прогон всех тестов | Проверка |
| 10 | Валидация | Баланс массы (вода гидратов) | Средняя |
| 11 | Валидация | LOI/H₂O проверка | Средняя |
| 12 | Валидация | Fe₂O₃/FeO режим в конфиге | Лёгкая |
| 13 | Расширение | Заглушки глауконита/биотита | Лёгкая |
| 14 | Расширение | Калибратор k_or | Средняя |
| 15 | Расширение | Property-based тесты (Hypothesis) | Средняя |
| 16 | Архитектура | AlgorithmFactory | Лёгкая |
| 17 | Архитектура | Step recorder | Средняя |
| 18 | Архитектура | Theory vs VBA comparison tool | Средняя |
| 19 | Архитектура | Векторизованный numpy batch | Сложная |
| 20 | Тесты | Эталонные составы (учебники) | Лёгкая |
| 21 | Тесты | Граничные тесты (CaO=0, CO2=0, ...) | Лёгкая |

---

## Риски и open questions

1. **k_or калибровка**: начальные значения (0.1-1.0) — рекомендации. Нужна калибровка на реальных данных.
2. **Порядок карбонатов**: теория (файл 03) говорит "кальцит → доломит" или "доломит → кальцит" в зависимости от типа породы. Реализуем ли?
3. **Fe₂O₃/FeO**: теория (файл07) рекомендует явный параметр. Пока оставляем auto-режим.
4. **LOI/H₂O**: требует наличия LOI в входных данных. Если его нет — только пометка.
5. **Montmorillonite**: теория упоминает как опциональный для незрелых пород. Оставляем в current RealAlgorithm, не дублируем в theory.
