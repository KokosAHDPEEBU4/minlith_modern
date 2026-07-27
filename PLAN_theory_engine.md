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

## Порядок реализации

| Шаг | Что делаем | Сложность |
|-----|-----------|-----------|
| 1 | Создаём `stage1.py` — простые формулы, минимальная логика | Лёгкая |
| 2 | Создаём `stage2.py` — полевые шпаты + глины + k_or | Средняя |
| 3 | Создаём `stage3.py` — карбонаты + оксиды + кварц | Лёгкая |
| 4 | Создаём `theory_algorithm.py` — оркестратор | Лёгкая |
| 5 | Добавляем `k_or` в `AdaptiveCoefficients` | Лёгкая |
| 6 | Переключаем `calculator.py` на `TheoryAlgorithm` | Лёгкая |
| 7 | Переименовываем `RealAlgorithm` → `VbaPortStub` | Лёгкая |
| 8 | Добавляем тест из файла 06 | Средняя |
| 9 | Запускаем полный прогон тестов | Проверка |

---

## Риски и.open questions

1. **k_or калибровка**: начальные значения (0.1-1.0) — это рекомендации. Нужна калибровка на реальных данных или учебных примерах.
2. **Порядок карбонатов**: теория (файл 03) говорит "кальцит → доломит" или "доломит → кальцит" в зависимости от типа породы. Нужно решить, реализовывать ли эту ветку.
3. **Fe₂O₃/FeO разделение**: теория (файл07) рекомендует делать это явным параметром. Пока оставляем как есть (Fe₂O₃ → 0.9*FeO в Stage 0).
4. **LOI/H₂O валидация**: теория (файл07) требует проверку покрытия воды. Это отдельная задача, не включена в этот план.
