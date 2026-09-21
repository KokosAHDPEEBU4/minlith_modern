# MINLITH Modern — Сценарии использования

Версия: 0.4.0 | Дата: 2026-07-23

---

## 1. Ядро расчёта (src/core/)

### 1.1 OxideComposition — входные данные

```python
@dataclass(frozen=True)
class OxideComposition:
    sio2: float = 0.0
    tio2: float = 0.0
    al2o3: float = 0.0
    fe2o3: float = 0.0
    feo: float = 0.0
    mgo: float = 0.0
    cao: float = 0.0
    na2o: float = 0.0
    k2o: float = 0.0
    p2o5: float = 0.0
    mno: float = 0.0
    c: float = 0.0
    so3: float = 0.0
    f: float = 0.0
    cl: float = 0.0
    s: float = 0.0
    co2: float = 0.0
    so: float = 0.0
```

**Методы:**
| Метод | Вход | Выход | Описание |
|---|---|---|---|
| `sum()` | — | `float` | Сумма всех 18 оксидов |
| `to_array()` | — | `np.ndarray(18,)` | Конвертация в numpy |
| `from_dict(data)` | `dict[str, float]` | `OxideComposition` | Создание из словаря |

---

### 1.2 Sample — входной образец

```python
@dataclass(frozen=True)
class Sample:
    name: str                          # Название образца
    composition: OxideComposition      # Химический состав
```

**Вход:** файл .xlsx/.csv → парсинг → `Sample(name="T-O2", composition=OxideComposition(sio2=52.5, ...))`

---

### 1.3 CalculationConfig — параметры расчёта

```python
@dataclass(frozen=True)
class CalculationConfig:
    molar_mass_source: str = "iupac"           # "iupac" | "minlith"
    custom_molar_masses: dict = {}             # Переопределение м.д.
    sum_tolerance: tuple[float, float] = (98.0, 102.0)  # Диапазон суммы
    warn_negative: bool = True                 # Предупреждать об отр. значениях
    auto_correct_sum: bool = False             # Автокоррекция до 100%
    decimal_places: int = 2                    # Знаков после запятой
    include_formula_units: bool = False        # Включить ФЕ в вывод
    include_defect: bool = True                # Включить дефект
    include_parameters: bool = True            # Включить параметры
    timeout_seconds: int = 120                 # Таймаут (сек)
    batch_size: int | str = "auto"             # Размер батча
```

---

### 1.4 validate_sample() — валидация

```python
def validate_sample(
    composition: OxideComposition,   # ВХОД: состав оксидов
    config: CalculationConfig,       # ВХОД: конфигурация
) -> tuple[bool, list[str]]:        # ВЫХОД: (валидность, предупреждения)
```

**Логика:**
```
ВХОД: OxideComposition, CalculationConfig
  │
  ├── Проверка суммы
  │     total = composition.sum()
  │     lo, hi = config.sum_tolerance  (по умолчанию 98.0, 102.0)
  │     ├── total < lo → warning: "Сумма {total:.2f}% ниже {lo}-{hi}%"
  │     ├── total > hi → warning: "Сумма {total:.2f}% выше {lo}-{hi}%"
  │     └── lo ≤ total ≤ hi → OK
  │
  ├── Проверка отрицательных значений
  │     Для каждого оксида (18 штук):
  │     ├── value < 0 → warning + is_valid = False
  │     └── value ≥ 0 → OK
  │
  ├── Проверка NaN/inf
  │     Для каждого float-значения:
  │     ├── value != value (NaN) → warning + is_valid = False
  │     ├── |value| == inf → warning + is_valid = False
  │     └── нормальное → OK
  │
  └── ВЫХОД: (is_valid, warnings)
        is_valid: bool — True если нет отрицательных/NaN/inf
        warnings: list[str] — список предупреждений
```

---

### 1.5 AdaptiveCoefficients — коэффициенты хлорита

```python
@dataclass(frozen=True)
class AdaptiveCoefficients:
    k1: float   # Mg в хлорите
    k2: float   # Fe в хлорите
    k3: float   # Al в хлорите
    k4: float   # Si в хлорите (k4 = 10 - k1 - k2 - 2*k3)
    F: float    # Fe3+/ΣFe (0.0–1.0)
    A: float    # Al/(Al+Fe)
```

**Метод:**
```python
AdaptiveCoefficients.from_F(F: float, A: float) -> AdaptiveCoefficients
```

---

### 1.6 calculate_coefficients() — вычисление k1-k4

```python
@lru_cache(maxsize=1024)
def calculate_coefficients(F: float, A: float) -> AdaptiveCoefficients
```

**ВХОД:** F (float, 0.0–1.0), A (float)
**ВЫХОД:** AdaptiveCoefficients
**Примечание:** Функция декорирована `@lru_cache(maxsize=1024)` для кэширования результатов вычислений коэффициентов. При повторных вызовах с теми же параметрами F и A возвращается закэшированный результат.

**Логика (5 диапазонов F):**
```
ВХОД: F, A
  │
  ├── F ∈ [0.0, 0.21)
  │     k1 = -5.18*F + 4.42
  │     k2 = 4.09*F
  │     k3 = (3.16 - 0.41*F) / 2
  │
  ├── F ∈ [0.21, 0.51)
  │     k1 = 3.93 - 2.96*F
  │     k2 = 5.66*F - 0.34
  │     k3 = (3.66 - 2.69*F) / 2
  │
  ├── F ∈ [0.51, 0.70)
  │     k1 = 5.13 - 5.32*F
  │     k2 = 2.54*F + 1.24
  │     k3 = (3.46*F + 0.53) / 2
  │
  ├── F ∈ [0.70, 0.87)
  │     k1 = max(6.2 - 12*F, 0.0)
  │     k2 = 2.54*F + 1.24
  │     k3 = (3.46*F + 0.53) / 2
  │
  └── F ∈ [0.87, 1.0]
        k1 = max(4 - 4*F, 0.0)
        k2 = 18.36*F - 12.36
        k3 = (25 - 25*F) / 2
  │
  ├── k4 = 10 - k1 - k2 - 2*k3
  │
  └── ВЫХОД: AdaptiveCoefficients(k1, k2, k3, k4, F, A)
```

**Ошибки:** `ValueError` если F < 0 или F > 1.0

---

### 1.7 AlgorithmInput / AlgorithmOutput — протокол алгоритма

```python
@dataclass(frozen=True)
class AlgorithmInput:
    sio2: float      # Si° (ф.е.)
    tio2: float      # Ti°
    al2o3: float     # Al°
    feo: float       # Fe° total (ф.е.)
    mgo: float       # Mg°
    cao: float       # Ca° (вычтен апатит)
    na2o: float      # Na° (вычтен галит)
    k2o: float       # K°
    p2o5: float      # P°
    mno: float       # Mn°
    c: float         # C°
    so3: float       # SO3°
    f: float         # F° (вычтен флюорит)
    cl: float        # Cl°
    s: float         # S°
    k1: float        # Коэффициент
    k2: float
    k3: float
    k4: float
    F: float
    A: float
    rock_type: int   # 1-5
```

```python
@dataclass
class AlgorithmOutput:
    Ab: float = 0.0    # Альбит
    An: float = 0.0    # Анортит
    Or: float = 0.0    # Ортоклаз
    Ill: float = 0.0   # Иллит
    Chl: float = 0.0   # Хлорит
    Kn: float = 0.0    # Каолинит
    Mm: float = 0.0    # Монтмориллонит
    Gb: float = 0.0    # Гиббсит
    Q: float = 0.0     # Кварц
    Dl: float = 0.0    # Доломит
    Ank: float = 0.0   # Анкерит
    Cc: float = 0.0    # Кальцит
    Rch: float = 0.0   # Родохрозит
    Sd: float = 0.0    # Сидерит
    Srp: float = 0.0   # Серпентин
    Mst: float = 0.0   # Магнезит
    Ht: float = 0.0    # Гематит
    Prl: float = 0.0   # Пиролюзит
```

**Протокол:**
```python
class MineralAlgorithm(Protocol):
    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput: ...
```

**ВХОД:** AlgorithmInput (18 ф.е. + 6 коэффициентов + тип породы)
**ВЫХОД:** AlgorithmOutput (18 минералов в ф.е., допускаются отрицательные)

---

### 1.8 Calculator — главный оркестратор

```python
class Calculator:
    def __init__(
        self,
        config: CalculationConfig | None = None,    # ВХОД: настройки
        algorithm: MineralAlgorithm | None = None,   # ВХОД: движок (excel_parity/geological_theory/python_rework)
    )

    def calculate_single(self, sample: Sample) -> CalculationResult
```

**ВХОД:** `Sample` (название + 18 оксидов в м.д.%)
**ВЫХОД:** `CalculationResult`

**Полная логика calculate_single():**
```
ВХОД: Sample(name="T-O2", composition=OxideComposition(sio2=52.5, ...))
  │
  ├── 0. Подготовка
  │     ├── Валидация: validate_sample(composition, config)
  │     │     └── Если is_valid=False → warnings, но расчёт продолжается
  │     ├── Выбор молярных масс: MOLAR_MASSES_IUPAC или MOLAR_MASSES_MINLITH
  │     └── Создание DebugTraceCollector
  │
  ├── 1. Конвертация масс→ф.е. (Stage 0)
  │     oxides = composition.to_array()                     # numpy(18,)
  │     molar_arr = [masses[k] for k in OXIDE_ORDER]       # numpy(18,)
  │     fe = oxides / molar_arr * 10000                     # ф.е. (м.д.% → ф.е.)
  │
  ├── 2. Коррекция CaO (апатит)
  │     apatite_ca = 3.36 * p2o5_м.д.% / masses["p2o5"] * 10000
  │     fe[cao_idx] -= apatite_ca
  │
  ├── 3. Коррекция F (флюорит)
  │     fe[f_idx] -= 0.67 * fe[p2o5_idx]
  │
  ├── 4. Коррекция Na₂O (галит)
  │     fe[na2o_idx] -= fe[cl_idx] / 2
  │
  ├── 5. Clamp отрицательных ф.е.
  │     np.clip(fe, 0, None, out=fe)
  │
  ├── 6. Вычисление F и A
  │     F = fe2o3_fu / (fe2o3_fu + feo_fu)     # Fe3+/ΣFe
  │     A = al2o3_fu / (al2o3_fu + fe_total_fu) # Al/(Al+Fe)
  │
  ├── 7. Коэффициенты: calculate_coefficients(F, A)
  │     └── → AdaptiveCoefficients(k1, k2, k3, k4, F, A)
  │
  ├── 8. Классификация типа породы: _classify_type(al, na, k, mg, coeff)
  │     TYPE_1: Al ≤ 1.2Na + K
  │     TYPE_2: Al ≤ 1.2Na + 3.25K
  │     TYPE_3: Al ≤ 1.2Na + 3.25K + (Mg-0.5K*k3)/k1
  │     TYPE_4: Al ≤ 5Na + 3.25K + (Mg-0.5K-2Na)*k3/k1
  │     TYPE_5: всё остальное
  │
  ├── 9. Построение AlgorithmInput
  │     _build_algorithm_input(fe, coeff, rock_type) → AlgorithmInput
  │
  ├── 10. Расчёт минералов: algorithm.compute(inp)
  │     ВХОД: AlgorithmInput (18 ф.е. + коэф. + тип)
  │     ВЫХОД: AlgorithmOutput (18 минералов в ф.е.)
  │     └── Currently: GeologicalTheoryAlgorithm (по теории)
  │
  ├── 11. Конвертация ф.е. → м.д.%
  │     _to_weight_percent(minerals_fu) → minerals_wt
  │     Каждый минерал: fw[mineral] * fu / 10000
  │
  ├── 12. Нормализация
  │     _normalize(minerals_wt) → (normalized, factor)
  │     total = sum всех минералов
  │     normalized = minerals * (100.0 / total)
  │
  ├── 13. Расчёт дефекта
  │     defect[oxide] = input_oxide - Σ(mineral_contribution)
  │
  └── ВЫХОД: CalculationResult
        sample_name: str
        input_composition: OxideComposition     # Исходные 18 оксидов
        formula_units: FormulaUnits              # Ф.е. после коррекций
        coefficients: AdaptiveCoefficients       # k1-k4, F, A
        rock_type: RockType                      # TYPE_1..TYPE_5
        minerals_formula: MineralComposition     # Минералы в ф.е.
        minerals_weight: MineralComposition      # Минералы в м.д.%
        defect: dict[str, float]                 # Дефект по оксидам
        warnings: list[str]                      # Предупреждения
        debug_trace: object | None               # Трассировка
```

---

### 1.9 CalculationResult — полный результат

```python
@dataclass(frozen=True)
class CalculationResult:
    sample_name: str                           # "T-O2"
    input_composition: OxideComposition        # Исходные оксиды
    formula_units: FormulaUnits                # Ф.е. (18 полей + corrected)
    coefficients: AdaptiveCoefficients         # k1-k4, F, A
    rock_type: RockType                        # TYPE_1..TYPE_5
    minerals_formula: MineralComposition       # 22+ минерала в ф.е.
    minerals_weight: MineralComposition        # 22+ минерала в м.д.%
    defect: dict[str, float]                   # {"sio2": -0.5, ...}
    warnings: list[str]                        # ["Сумма 97.5%偏低..."]
    debug_trace: object | None = None
```

---

### 1.10 AnomalyDetector — обнаружение аномалий

```python
@dataclass
class AnomalyHypothesis:
    severity: str                  # "info" | "warning" | "critical"
    pattern: str                   # Идентификатор правила (например "high_ca_so3")
    message: str                   # Описание аномалии
    confidence: float              # 0.0–1.0 (уверенность)
    suggested_action: str          # Рекомендация
    affected_oxides: list[str]     # Затронутые оксиды (например ["cao", "so3"])


class AnomalyDetector:
    def analyze(self, result: CalculationResult) -> list[AnomalyHypothesis]
    def analyze_batch(self, results: list[CalculationResult]) -> dict[str, list[AnomalyHypothesis]]
```

**Вход:** `CalculationResult` (один или список)
**Выход:** `list[AnomalyHypothesis]` или `dict[str, list[AnomalyHypothesis]]`

#### Встроенные правила (10 штук)

| # | pattern | Описание | severity |
|---|---|---|---|
| 1 | `high_ca_so3` | Высокое CaO при повышенном SO₃ (гипс) | warning |
| 2 | `low_sum` | Сумма оксидов < 98% | warning |
| 3 | `high_sum` | Сумма оксидов > 102% | warning |
| 4 | `iron_rich` | Повышенное содержание железа (> 15% Fe₂O₃+FeO) | info |
| 5 | `apatite_incomplete` | Неполная коррекция апатита (P₂O₅ > 0.5%) | warning |
| 6 | `critical_defect` | Критический дефект (> 5% по какому-то оксиду) | critical |
| 7 | `carbonate_incomplete` | Неполная коррекция карбонатов (CaO+MgO > 20%) | warning |
| 8 | `feldspar_anomaly` | Аномалия полевых шпатов (Ab+An+Or > 50%) | info |
| 9 | `high_phosphorus` | Высокое содержание фосфора (P₂O₅ > 2%) | warning |
| 10 | `negative_mineral` | Отрицательные минералы в результате | warning |

#### Интеграция с CalculationResult

Аномалии хранятся в поле `anomalies` класса `CalculationResult`:

```python
@dataclass(frozen=True)
class CalculationResult:
    sample_name: str
    input_composition: OxideComposition
    formula_units: FormulaUnits
    coefficients: AdaptiveCoefficients
    rock_type: RockType
    minerals_formula: MineralComposition
    minerals_weight: MineralComposition
    defect: dict[str, float]
    warnings: list[str]
    anomalies: list[AnomalyHypothesis] = ()  # ← НОВОЕ ПОЛЕ
    debug_trace: object | None = None
```

---

### 1.11 Explainer — объяснение результатов

```python
class Explainer:
    def __init__(self, config: CalculationConfig | None = None)

    def explain(
        self,
        result: CalculationResult,
        level: str = "standard",   # "brief" | "standard" | "detailed"
    ) -> str

    def explain_step(
        self,
        result: CalculationResult,
        step: str,                  # "coefficients" | "minerals" | "anomalies" | "all"
    ) -> str
```

**Вход:** `CalculationResult` + уровень детализации
**Выход:** Строка с текстовым описанием

#### Уровни детализации

| level | Описание |
|---|---|
| `"brief"` | Тип породы + доминирующие минералы (1–2 предложения) |
| `"standard"` | Тип + коэффициенты + ключевые минералы + аномалии |
| `"detailed"` | Полное описание: тип породы, коэффициенты, ключевые шаги алгоритма, доминирующие минералы, аномалии |

#### Формат вывода (detailed)

```
Тип породы: TYPE_5 (глинистая порода)

Коэффициенты хлорита:
  F = 0.425 (Fe³⁺/ΣFe)
  A = 0.879 (Al/(Al+Fe))
  k1 = 0.56, k2 = 1.23, k3 = 0.89, k4 = 5.43

Ключевые шаги:
  1. Коррекция CaO: апатит (P₂O₅ = 0.8%) → 3.36 × 0.8 / 141.94 × 10000 = 189.1 ф.е.
  2. Коррекция F: флюорит → 0.67 × F°
  3. Коррекция Na₂O: галит → Cl° / 2

Доминирующие минералы:
  Иллит: 36.26%
  Хлорит: 25.74%
  Кварц: 31.38%

Аномалии:
  [warning] iron_rich: Высокое содержание железа (18.5%)
```

---

### 2.0 MineralComposition — минеральный состав

```python
@dataclass(frozen=True)
class MineralComposition:
    # Полевые шпаты
    ab: float = 0.0      # Альбит
    an: float = 0.0      # Анортит
    pl: float = 0.0      # Плагиоклаз (Ab+An)
    or_: float = 0.0     # Ортоклаз
    # Глинистые минералы
    ill: float = 0.0     # Иллит
    chl: float = 0.0     # Хлорит
    kn: float = 0.0      # Каолинит
    mm: float = 0.0      # Монтмориллонит
    gb: float = 0.0      # Гиббсит
    # Карбонаты
    cc: float = 0.0      # Кальцит
    dl: float = 0.0      # Доломит
    ank: float = 0.0     # Анкерит
    rch: float = 0.0     # Родохрозит
    sd: float = 0.0      # Сидерит
    # Прочие
    q: float = 0.0       # Кварц
    ap: float = 0.0      # Апатит
    c: float = 0.0       # Углерод
    srp: float = 0.0     # Серпентин
    mst: float = 0.0     # Магнезит
    ht: float = 0.0      # Гематит
    prl: float = 0.0     # Пиролюзит
    pr: float = 0.0      # Пирит
    rt: float = 0.0      # Рутил
    hl: float = 0.0      # Галит
    gy: float = 0.0      # Гипс
    fl: float = 0.0      # Флюорит
    # Производные группы
    fsp: float = 0.0     # Фельдшпаты (Ab+An+Or)
    pel: float = 0.0     # Пелиты (Ill+Chl+Kn+Mm+Gb)
    pel_fsp: float = 0.0 # Пелиты+фельдшпаты
    carsd: float = 0.0   # Карбонаты (Cc+Dl+Ank+Rch+Sd)
    ill_kn: float = 0.0  # Ill+Kn
    chl_mm_srp: float = 0.0  # Chl+Mm+Srp
```

**Метод:** `sum_formula_units() -> float` — сумма базовых минералов

---

## 2. Ввод/вывод данных (src/io/)

### 2.1 load_samples() — загрузка Excel

```python
def load_samples(path: str | Path) -> list[Sample]
```

**ВХОД:** путь к .xlsx или .xls файлу
**ВЫХОД:** `list[Sample]`

**Логика:**
```
ВХОД: path = "data/samples.xlsx"
  │
  ├── Проверка расширения
  │     ├── .xlsx → openpyxl
  │     └── .xls → xlrd
  │
  ├── Поиск листа с данными
  │     Ищет лист содержащий "ИСХ" или "ДАННЫЕ" или первый непустой
  │
  ├── Определение формата
  │     ├── Формат 1 (ИСХ ДАННЫЕ): строки=оксиды, столбцы=образцы
  │     │     Row 1: заголовки (названия образцов)
  │     │     Rows 2-19: значения оксидов (SiO2..SO)
  │     │     Column A: названия оксидов
  │     │
  │     └── Формат 2 (транспонированный): столбцы=оксиды, строки=образцы
  │           Column A: названия оксидов
  │           Columns B+: данные образцов
  │
  ├── Парсинг каждого столбца/строки
  │     name = заголовок столбца (row 1)
  │     oxides = {оксид: float(значение)} для 18 оксидов
  │     Sample(name=name, composition=OxideComposition(**oxides))
  │
  └── ВЫХОД: [Sample, Sample, ...]
```

**Ошибки:** `FileNotFoundError`, `ValueError("Неподдерживаемый формат")`

---

### 2.2 read_csv() — загрузка CSV

```python
def read_csv(path: Path, separator: str | None = None) -> list[Sample]
```

**ВХОД:** путь к .csv, опциональный разделитель
**ВЫХОД:** `list[Sample]`

**Логика:**
```
ВХОД: path = "data/samples.csv"
  │
  ├── Автоопределение кодировки
  │     Пробует: utf-8-sig → utf-8 → cp1251 → latin-1
  │     Если все неудачны → utf-8-sig
  │
  ├── Автоопределение разделителя
  │     Читает первую строку
  │     Если ";" in first_line → separator = ";"
  │     Иначе → separator = ","
  │
  ├── Парсинг CSV
  │     DictReader(f, delimiter=separator)
  │     Для каждой строки:
  │       name = row["Name"] | row["name"] | row["Образец"] | row["Sample"] | "Sample_N"
  │       oxides = {}
  │       Для каждого оксида (18 штук):
  │         val = row[оксид] | row[Label] | row[UPPER] | row[lower] | "0"
  │         oxides[оксид] = float(val.replace(",", "."))
  │
  └── ВЫХОД: [Sample(name="T-O2", composition=OxideComposition(...)), ...]
```

---

### 2.3 load_samples_from_zip() — загрузка ZIP

```python
def load_samples_from_zip(path: str | Path) -> list[Sample]
```

**ВХОД:** путь к .zip файлу
**ВЫХОД:** `list[Sample]` (объединённые из всех файлов)

**Логика:**
```
ВХОД: path = "data/archive.zip"
  │
  ├── Проверка: zipfile.is_zipfile(path)
  │     └── Нет → ValueError("Not a valid ZIP file")
  │
  ├── Извлечение во временную папку
  │     tempfile.TemporaryDirectory(prefix="minlith_zip_")
  │     zipfile.ZipFile.extractall(tmp)
  │
  ├── Рекурсивный поиск файлов
  │     rglob("*") с расширениями: .xlsx, .xls, .csv
  │
  ├── Загрузка каждого файла
  │     .xlsx/.xls → load_samples(f)
  │     .csv → read_csv(f)
  │
  └── ВЫХОД: list[Sample] (все образцы из всех файлов)
```

---

### 2.4 save_results() — экспорт в Excel

```python
def save_results(path: Path, results: list[CalculationResult]) -> None
```

**ВХОД:** путь + список CalculationResult
**ВЫХОД:** .xlsx файл

**Структура выходного файла:**
```
Лист 1: "Результаты"
  Row 1: Образец | Тип | F | A | k1 | k2 | k3 | k4 | Ab | An | Or | Q | ...
  Row 2: T-O2    | 5   | 0.425 | ... | 7.82 | 0 | 5.53 | 31.38 | ...

Лист 2: "Формулы единицы" (если include_formula_units=True)
  Аналогичная структура, но значения в ф.е.

Лист 3: "Дефект" (если include_defect=True)
  Row 1: Образец | ΔSiO₂ | ΔTiO₂ | ΔAl₂O₃ | ...
  Row 2: T-O2    | -0.5  | 0.1   | 0.3    | ...
```

---

### 2.5 save_results_json() — экспорт в JSON

```python
def save_results_json(path: Path, results: list[CalculationResult]) -> None
```

**ВХОД:** путь + список CalculationResult
**ВЫХОД:** .json файл

**Формат:**
```json
[
  {
    "sample_name": "T-O2",
    "rock_type": 5,
    "coefficients": {"F": 0.425, "A": 0.879, "k1": 0.56, "k2": 1.23, "k3": 0.89, "k4": 5.43},
    "minerals_weight": {"ab": 7.82, "an": 0.0, "or_": 5.53, "q": 31.38, "ill": 36.26, "chl": 25.74, "kn": -9.77},
    "defect": {"sio2": -0.5, "al2o3": 0.3, "fe2o3": 0.1}
  }
]
```

---

### 2.6 write_csv() — экспорт в CSV

```python
def write_csv(path: Path, results: list, separator: str = ";") -> None
```

**ВХОД:** путь + список CalculationResult + разделитель
**ВЫХОД:** .csv файл

**Формат:**
```
Sample;Type;F;A;ab_wt%;an_wt%;or_wt%;q_wt%;ill_wt%;chl_wt%;kn_wt%;...
T-O2;5;0.4250;0.8790;7.82;0.00;5.53;31.38;36.26;25.74;-9.77;...
```

---

### 2.7 save_results() — экспорт в Excel (детально)

```python
def save_results(path: str | Path, results: list[CalculationResult]) -> None
```

**ВХОД:** путь (str|Path) + list[CalculationResult]
**ВЫХОД:** .xlsx файл с автоподбором ширины столбцов

---

### 2.8 XRFImporter — импорт XRF данных

```python
def read_xrf(path: str | Path) -> list[Sample]
```

**ВХОД:** путь к файлу (CSV или TXT)
**ВЫХОД:** `list[Sample]`
**Описание:** Автоопределение формата (Bruker/Panalytical CSV или Bruker TXT).

#### read_xrf_csv()
```python
def read_xrf_csv(path: str | Path) -> list[Sample]
```

**ВХОД:** путь к CSV-файлу XRF-анализатора
**ВЫХОД:** `list[Sample]`
**Описание:** Парсинг CSV-файлов Bruker/S8 Tiger или Panalytical Axios.

#### read_xrf_txt()
```python
def read_xrf_txt(path: str | Path) -> list[Sample]
```

**ВХОД:** путь к TXT-файлу Bruker-style
**ВЫХОД:** `list[Sample]`
**Описание:** Парсинг текстовых отчётов Bruker (S8 Tiger, TRACER).

#### Маппинг алиасов элементов

XRF-анализаторы возвращают символы элементов, которые маппятся на оксиды:

| Элемент | Оксид | Множитель |
|---|---|---|
| Si | SiO₂ | × 2.1393 |
| Ti | TiO₂ | × 1.6681 |
| Al | Al₂O₃ | × 1.8895 |
| Fe | Fe₂O₃ | × 1.4297 (или FeO × 1.2865) |
| Mg | MgO | × 1.6582 |
| Ca | CaO | × 1.3992 |
| Na | Na₂O | × 1.3480 |
| K | K₂O | × 1.2046 |
| P | P₂O₅ | × 2.2914 |
| Mn | MnO | × 1.2909 |
| S | SO₃ | × 2.4971 |
| Ba | BaO | × 1.1165 |
| Sr | SrO | × 1.1822 |
| Zr | ZrO₂ | × 1.3508 |
| Rb | Rb₂O | × 1.0924 |

---

## 3. База данных (src/database/)

### 3.1 SampleRepository — CRUD

```python
class SampleRepository:
    def __init__(self, session: Session | None = None)
```

**Методы:**

#### save_sample()
```python
def save_sample(self, sample: Sample) -> int
```
**ВХОД:** Sample
**ВЫХОД:** `int` — ID сохранённого образца
**Действие:** Создаёт запись в таблице `samples` + `sample_oxides`

#### save_result()
```python
def save_result(self, result: CalculationResult) -> int
```
**ВХОД:** CalculationResult
**ВЫХОД:** `int` — ID расчёта
**Действие:**
```
ВХОД: CalculationResult
  │
  ├── Поиск/создание образца
  │     SampleDB.filter_by(name=result.sample_name).first()
  │     ├── Найден → использовать существующий
  │     └── Не найден → создать новый + сохранить оксиды
  │
  ├── Создание расчёта
  │     CalculationDB(sample_id, rock_type, F, A, k1-k4, warnings)
  │
  ├── Сохранение минералов
  │     Для каждого минерала (25 полей):
  │     CalculationMineralDB(calculation_id, mineral, formula_units, weight_percent)
  │
  └── ВЫХОД: db_calc.id
```

#### get_recent_results()
```python
def get_recent_results(self, limit: int = 50) -> list[dict]
```
**ВХОД:** limit (int)
**ВЫХОД:** `list[dict]` — каждый dict:
```python
{
    "id": int,              # ID расчёта
    "sample_id": int,       # ID образца
    "sample": str,          # Название образца
    "rock_type": int,       # Тип породы (1-5)
    "F": float,             # Коэффициент F
    "A": float,             # Коэффициент A
    "minerals": dict,       # {"ab": 7.82, "an": 0.0, ...}
    "created_at": str,      # ISO timestamp
}
```

#### list_samples()
```python
def list_samples(self, limit: int = 100) -> list[tuple[int, str]]
```
**ВХОД:** limit
**ВЫХОД:** `[(id, name), ...]`

#### delete_sample()
```python
def delete_sample(self, sample_id: int) -> None
```
**ВХОД:** sample_id (int)
**ВЫХОД:** None
**Действие:** Удаляет образец + связанные расчёты (CASCADE)

#### search_samples()
```python
def search_samples(self, query: str) -> list[tuple[int, str]]
```
**ВХОД:** query (str) — 부분 совпадение имени
**ВЫХОД:** `[(id, name), ...]`

#### cleanup_old_records()
```python
def cleanup_old_records(self, keep_last: int = 100) -> int
```
**ВХОД:** keep_last (int)
**ВЫХОД:** `int` — количество удалённых записей
**Действие:** Удаляет все расчёты кроме последних keep_last

#### get_stats()
```python
def get_stats(self) -> dict
```
**ВХОД:** —
**ВЫХОД:**
```python
{
    "samples": int,       # Количество образцов
    "calculations": int,  # Количество расчётов
    "db_size_mb": float,  # Размер БД в МБ
}
```

---

## 4. Кэширование (src/utils/cache.py)

### 4.1 ResultCache

```python
class ResultCache:
    def __init__(self, cache_dir: Path | str | None = None)
```

**Путь по умолчанию:** `~/.minlith/cache/`

#### get()
```python
def get(self, file_path: Path | str) -> list[dict] | None
```
**ВХОД:** путь к файлу
**ВЫХОД:** `list[dict] | None` — кэшированные результаты или None

**Логика:**
```
ВХОД: file_path = "data/samples.xlsx"
  │
  ├── Вычисление хэша: sha256_file(file_path) → "a1b2c3..."
  │
  ├── Поиск в index.json
  │     entry = index[hash]
  │     ├── Не найден → return None
  │     └── Найден → проверка файла
  │
  ├── Проверка existence
  │     result_path = cache_dir / entry["result_file"]
  │     ├── Файл удалён → удалить из index, return None
  │     └── Файл существует → чтение
  │
  └── ВЫХОД: json.loads(result_path.read_text()) → list[dict]
```

#### put()
```python
def put(self, file_path: Path | str, results: list) -> None
```
**ВХОД:** путь к файлу + list[CalculationResult]
**ВЫХОД:** — (запись в кэш)

**Логика:**
```
ВХОД: file_path, [CalculationResult, ...]
  │
  ├── Хэш: sha256_file(file_path)
  │
  ├── Сериализация results
  │     Для каждого CalculationResult:
  │     {sample_name, rock_type, F, A, minerals: {ab: ..., an: ...}, defect: {...}}
  │
  ├── Запись: cache_dir / "{hash}.json"
  │
  └── Обновление index.json
```

#### invalidate()
```python
def invalidate(self, file_path: Path | str) -> bool
```
**ВХОД:** путь к файлу
**ВЫХОД:** `bool` — True если удалено

---

## 5. Диаграммы (src/charts/)

### 5.1 ChartData — контейнер данных

```python
@dataclass
class ChartData:
    sample_names: list[str] = []            # ["T-O2", "T-O3", ...]
    oxides: dict[str, np.ndarray] = {}      # {"sio2": array([52.5, ...]), ...}
    minerals_wt: dict[str, np.ndarray] = {} # {"ab": array([7.82, ...]), ...}
    minerals_fu: dict[str, np.ndarray] = {} # {"ab": array([...]), ...}
    defect: dict[str, np.ndarray] = {}      # {"sio2": array([-0.5, ...]), ...}
    rock_types: list[int] = []              # [5, 3, 1, ...]
    F_values: list[float] = []              # [0.425, ...]
    A_values: list[float] = []              # [0.879, ...]
    metadata: dict[str, Any] = {}
```

---

### 5.2 ChartPlugin — интерфейс диаграмм

```python
class ChartPlugin(ABC):
    def get_name(self) -> str                          # "Mineral Bar Chart"
    def get_description(self) -> str                   # "Столбчатая диаграмма минералов"
    def requires_minerals(self) -> bool                # True/False
    def requires_oxides(self) -> bool                  # True/False
    def render(self, data: ChartData, **kwargs) -> Any # → matplotlib.Figure
    def export(self, data: ChartData, path: Path, fmt="png", dpi=150) -> None
```

---

### 5.3 BUILTIN_CHARTS — список всех диаграмм

| # | get_name() | requires_minerals | requires_oxides | Описание |
|---|---|---|---|---|
| 1 | Mineral Bar Chart | True | False | Столбчатая минералов |
| 2 | Mineral Pie | True | False | Круговая минералов |
| 3 | Defect Chart | False | True | Дефект оксидов |
| 4 | QAPF | True | False | Треугольник QAPF |
| 5 | TAS | False | True | Total Alkali vs Silica |
| 6 | A-CN-K | False | True | Аксонометрическая |
| 7 | Mineral Heatmap | True | False | Тепловая карта |
| 8 | Rock Type Distribution | True | False | Распределение типов |
| 9 | Feldspar Triangle | True | False | Треугольник полевых шпатов |
| 10 | Harker | False | True | Вариационные диаграммы |
| 11 | AFM | False | True | Треугольник AFM |
| 12 | SiO₂-K₂O | False | True | Диаграмма SiO₂-K₂O |
| 13 | Bland-Altman | False | True | Анализ различий |
| 14 | Correlation | False | True | Корреляционная матрица |
| 15 | KFChart | False | False | Зависимость k1-k4 от F |

---

### 5.4 Построение диаграммы (полный цикл)

```
ВХОД: list[CalculationResult]
  │
  ├── Построение ChartData
  │     data = ChartData()
  │     data.sample_names = [r.sample_name for r in results]
  │     data.minerals_wt["ab"] = np.array([r.minerals_weight.ab for r in results])
  │     data.oxides["sio2"] = np.array([r.input_composition.sio2 for r in results])
  │     data.rock_types = [int(r.rock_type) for r in results]
  │
  ├── Выбор диаграммы
  │     chart = BUILTIN_CHARTS[idx]  # ChartPlugin
  │
  ├── Рендер
  │     fig = chart.render(data)     # matplotlib.Figure
  │
  ├── Экспорт в файл
  │     chart.export(data, path, fmt="png", dpi=150)
  │     fig.savefig(path, format=fmt, dpi=dpi)
  │
  └── ВЫХОД: файл .png/.pdf/.svg/.html
```

---

## 6. Отчёты (src/reports/)

### 6.1 ReportTemplate — шаблон отчёта

```python
@dataclass
class ReportTemplate:
    name: str = "Standard"
    blocks: list[ReportBlock] = []
    metadata: dict[str, Any] = {}
```

### 6.2 ReportBlock — блок отчёта

```python
@dataclass
class ReportBlock:
    block_type: BlockType      # Тип блока
    title: str = ""            # Заголовок
    options: dict = {}         # Опции
    text_content: str = ""     # Для TEXT блока
    chart_type: str = ""       # Для CHART блока
    chart_sample_idx: int = 0
    show_minerals: list[str] = []
    min_wt_percent: float = 0.0
    sort_by: str = ""
```

### 6.3 BlockType — типы блоков

```python
class BlockType(Enum):
    HEADER = "header"              # Заголовок отчёта
    MINERAL_TABLE = "mineral_table" # Таблица минералов
    OXIDE_TABLE = "oxide_table"    # Таблица оксидов
    PARAMETERS = "parameters"      # Параметры расчёта (F, A, k1-k4)
    DEFECT = "defect"              # Таблица дефекта
    TEXT = "text"                  # Текстовый блок
    CHART = "chart"                # Диаграмма
    PAGE_BREAK = "page_break"      # Разрыв страницы
```

### 6.4 PREDEFINED_TEMPLATES — готовые шаблоны

```python
PREDEFINED_TEMPLATES: dict[str, Callable[[], ReportTemplate]] = {
    "brief": template_brief,
    "standard": template_standard,
    "full": template_full,
    "core": template_core,
    "geochemical": template_geochemical,
}
```

#### template_brief() — Краткий
```
Блоки:
  1. HEADER: "MINLITH Report — Краткий"
  2. PARAMETERS: параметры расчёта
  3. MINERAL_TABLE: все минералы
```

#### template_standard() — Стандартный
```
Блоки:
  1. HEADER: "MINLITH Report — Стандартный"
  2. PARAMETERS: параметры расчёта
  3. MINERAL_TABLE: все минералы
  4. DEFECT: дефект оксидов
```

#### template_full() — Полный
```
Блоки:
  1. HEADER: "MINLITH Report — Полный"
  2. TEXT: сводка (кол-во образцов, типы пород)
  3. PARAMETERS: параметры расчёта
  4. OXIDE_TABLE: входные оксиды
  5. MINERAL_TABLE: все минералы
  6. DEFECT: дефект оксидов
  7. PAGE_BREAK
```

#### template_core() — Керн
```
Блоки:
  1. HEADER: "MINLITH Report — Отчёт по керну"
  2. PARAMETERS: параметры расчёта
  3. OXIDE_TABLE: входные оксиды
  4. MINERAL_TABLE: все минералы
  5. DEFECT: дефект оксидов
```
**Назначение:** Отчёт по керну — оксиды + минералы + параметры, без диаграмм.

#### template_geochemical() — Геохимический
```
Блоки:
  1. HEADER: "MINLITH Report — Геохимический паспорт"
  2. TEXT: сводная информация (кол-во образцов, типы пород)
  3. PARAMETERS: параметры расчёта (F, A, k1-k4)
  4. OXIDE_TABLE: входные оксиды
  5. MINERAL_TABLE: все минералы
  6. DEFECT: дефект оксидов
  7. PAGE_BREAK
  8. CHART: TAS ( Total Alkali vs Silica )
  9. CHART: QAPF ( Треугольник )
```
**Назначение:** Геохимический паспорт — сводная + параметры + диаграммы.

---

### 6.5 PDFGenerator

```python
class PDFGenerator:
    def __init__(self, results: list[CalculationResult])
    def generate(self, path: Path, template: ReportTemplate | None, title: str = "MINLITH Report") -> None
```

**ВХОД:** path (Path), template (ReportTemplate), title (str)
**ВЫХОД:** PDF-файл

**Логика:**
```
ВХОД: path="report.pdf", template=template_standard(), results=[...]
  │
  ├── Создание документа
  │     SimpleDocTemplate(path, pagesize=A4, margins=15mm/20mm)
  │
  ├── Рендер каждого блока
  │     HEADER → Paragraph(title, ReportTitleStyle)
  │     MINERAL_TABLE → Table([Mineral, Sample1, Sample2, ...])
  │     OXIDE_TABLE → Table([Oxide, Sample1, Sample2, ...])
  │     PARAMETERS → Table([F, A, k1, k2, k3, k4])
  │     DEFECT → Table([ΔSiO₂, ΔAl₂O₃, ...])
  │     TEXT → Paragraph(text, NormalStyle)
  │     CHART → Image(fig, width=160mm, height=100mm)
  │     PAGE_BREAK → PageBreak()
  │
  ├── Нумерация страниц
  │     "MINLITH Report — стр. {N}"
  │
  └── ВЫХОД: PDF-файл
```

---

### 6.6 WordGenerator

```python
class WordGenerator:
    def __init__(self, results: list[CalculationResult])
    def generate(self, path: Path, template: ReportTemplate | None, title: str = "MINLITH Report") -> None
```

**ВХОД:** path (Path), template (ReportTemplate), title (str)
**ВЫХОД:** .docx файл

---

### 6.7 HTMLGenerator

```python
class HTMLGenerator:
    def __init__(self, results: list[CalculationResult])
    def generate(self, path: Path, template: ReportTemplate | None, title: str = "MINLITH Report") -> None
```

**ВХОД:** path (Path), template (ReportTemplate), title (str)
**ВЫХОД:** .html файл (jinja2 шаблон)

---

### 6.8 LaTeXExporter

```python
class LaTeXExporter:
    def __init__(self, results: list[CalculationResult])
    def export(
        self,
        path: Path,
        style: str = "gost",        # "gost" | "nature" | "springer"
        caption: str = "",           # Подпись к таблице
        label: str = "",             # LaTeX label
    ) -> Path
```

**ВХОД:** path (Path), style (str), caption (str), label (str)
**ВЫХОД:** .tex файл

**Стили:**
| Стиль | Описание |
|---|---|
| `"gost"` | ГОСТ 7.32 (академический стиль) |
| `"nature"` | Журнал Nature ( минималистичный) |
| `"springer"` | Springer LNCS (научные конференции) |

**Особенности:**
- Использует `booktabs` ( `\toprule`, `\midrule`, `\bottomrule` )
- Числовые столбцы через `siunitx` ( `S` тип столбца )
- Кодировка: `T2A` fontenc (кириллица)
- Автоматическое форматирование чисел с `decimal_places` из конфигурации

**Пример выходного .tex:**
```latex
\documentclass{article}
\usepackage[T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[english,russian]{babel}
\usepackage{booktabs}
\usepackage{siunitx}
\begin{document}
\begin{table}[htbp]
\caption{Результаты расчёта MINLITH}
\label{tab:minlith_results}
\centering
\begin{tabular}{lS[table-format=2.2]S[table-format=1.4]}
\toprule
{Образец} & {SiO₂} & {F} \\
\midrule
T-O2 & 52.50 & 0.4250 \\
T-O3 & 48.30 & 0.6120 \\
\bottomrule
\end{tabular}
\end{table}
\end{document}
```

---

## 7. GUI — полный цикл (src/gui/)

### 7.1 Запуск

```bash
python -m src gui
# или
from src.gui.main_window import MainWindow
app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
```

### 7.2 MainWindow — главное окно

```python
class MainWindow(QMainWindow):
    def __init__(self) -> None
```

**Внутренние компоненты:**
```
MainWindow
├── Sidebar (160px, 9 кнопок)
│     ├── Начало → WelcomePage
│     ├── Файлы → FilesPage
│     ├── Ввод → InputPage
│     ├── Результаты → ResultsPage
│     ├── Диаграммы → ChartsPage
│     ├── Отчёты → ReportsPage
│     ├── История → HistoryPage
│     ├── Настройки → SettingsPage
│     └── Журнал → LogsPage
│
├── QStackedWidget (страницы)
│
├── StatusBar: "Готово" / статус последнего действия
│
├── Горячие клавиши:
│     Ctrl+O → импорт файлов
│     Ctrl+S → экспорт результатов
│     Ctrl+E/I/R/D/P → переключение вкладок
│     F5 → расчёт
│
└── ConfigManager: сохранение геометрии окна
```

### 7.3 WelcomePage — начальная страница

```
ВХОД: —
ВЫХОД: Сигнал open_files → переключение на FilesPage
```

### 7.4 FilesPage — управление файлами

```python
class FilesPage(QWidget):
    samples_loaded = pyqtSignal(list)  # list[Sample]
```

**Вход:**
- Drag-drop файлов (.xlsx/.csv)
- Кнопка «Импорт .xlsx» → QFileDialog
- Кнопка «Импорт .csv» → QFileDialog

**Выход:**
- Сигнал `samples_loaded` → передаёт `list[Sample]` в MainWindow

**API вызовы:**
```
DragDropWidget.files_dropped → _on_files_dropped(paths)
  ├── _load_folder(folder)
  │     rglob("*.xlsx|*.csv") → load_samples(f) / read_csv(f)
  ├── _load_file(path)
  │     load_samples(path) → list[Sample]
  │     samples_loaded.emit(samples)
  └── _load_csv(path)
        read_csv(path) → list[Sample]
        samples_loaded.emit(samples)
```

### 7.5 InputPage — ручной ввод

```python
class InputPage(QWidget):
    calculation_done = pyqtSignal(object)  # CalculationResult
```

**Вход:**
- Таблица оксидов (18 полей, редактируемые)
- Название образца
- Кнопка «Рассчитать (F5)»

**Выход:**
- Сигнал `calculation_done` → передаёт `CalculationResult` в MainWindow

**API вызовы:**
```
_on_calculate()
  │
  ├── comp = OxideTable.get_composition() → OxideComposition
  │     Для каждого оксида: float(table.item(i,1).text())
  │
  ├── name = QLineEdit.text() → str
  │
  ├── Sample(name=name, composition=comp) → Sample
  │
  ├── Calculator.calculate_single(sample) → CalculationResult
  │
  └── calculation_done.emit(result)
```

### 7.6 ResultsPage — отображение результатов

**Вход:** `CalculationResult` (через `add_result()`)
**Выход:** Таблица + детальная таблица

**API вызовы:**
```
add_result(result)
  │
  ├── _rebuild_summary()
  │     Столбцы: ["Образец", "Тип", "F", "A", "Ab", "An", "Or", "Q", "Ill", "Chl", "Kn", "Mm", "Gb", "Ap", "Cc", "Dl"]
  │     Для каждого result: QTableWidgetItem(sample_name, rock_type.name, F, A, minerals...)
  │
  └── _on_selection_changed()
        r = self._results[idx]
        MineralTable.set_minerals(r.minerals_weight, r.minerals_formula)
```

### 7.7 ChartsPage — диаграммы

**Вход:** `ChartData` (через `set_data()`)
**Выход:** matplotlib Figure → QPixmap → отображение

**API вызовы:**
```
build_data_from_results(results) → ChartData
  │
  ├── data.sample_names = [r.sample_name for r in results]
  ├── data.minerals_wt[field] = np.array([getattr(r.minerals_weight, field) for r in results])
  ├── data.oxides[field] = np.array([getattr(r.input_composition, field) for r in results])
  ├── data.rock_types = [int(r.rock_type) for r in results]
  └── data.F_values = [r.coefficients.F for r in results]

_on_render()
  │
  ├── chart = BUILTIN_CHARTS[idx]
  ├── fig = chart.render(data)           # → matplotlib.Figure
  ├── buf = io.BytesIO()
  ├── fig.savefig(buf, format="png")     # → bytes
  ├── QPixmap.loadFromData(buf.read())   # → QPixmap
  └── self._chart_label.setPixmap(scaled)

_on_export()
  │
  ├── chart.export(data, path)           # → файл .png/.pdf/.svg
  └── QMessageBox("Экспортировано: {path}")
```

### 7.8 ReportsPage — отчёты

**Вход:** `list[CalculationResult]` + выбор шаблона/формата
**Выход:** PDF/Word/HTML файл

**API вызовы:**
```
_export(fmt="pdf")
  │
  ├── tmpl = _get_template()  → ReportTemplate
  │     idx=0 → template_brief()
  │     idx=1 → template_standard()
  │     idx=2 → template_full()
  │
  ├── fmt="pdf":
  │     PDFGenerator(results).generate(path, tmpl)  → PDF
  │
  ├── fmt="docx":
  │     WordGenerator(results).generate(path, tmpl) → DOCX
  │
  └── fmt="html":
        HTMLGenerator(results).generate(path, tmpl) → HTML
```

### 7.9 HistoryPage — история

**Вход:** — (загрузка из БД)
**Выход:** Таблица + экспорт CSV

**API вызовы:**
```
_load_data()
  │
  ├── repo = SampleRepository()
  ├── results = repo.get_recent_results(limit=500) → list[dict]
  └── _populate_table(results)

_on_delete()
  │
  ├── repo.delete_sample(sample_id)
  └── _load_data()  # обновление

_on_export()
  │
  ├── QFileDialog → path
  ├── csv.writer → CSV файл
  └── QMessageBox("Экспортировано {N} записей")
```

### 7.10 SettingsPage — настройки

**Вход:** ConfigManager
**Выход:** Сохранение в JSON

**API вызовы:**
```
_on_save()
  │
  ├── config["molar_mass_source"] = "iupac"|"minlith"
  ├── config["sum_tolerance"] = [lo, hi]
  ├── config["warn_negative"] = True|False
  ├── config["auto_correct_sum"] = True|False
  ├── config["decimal_places"] = 0..6
  ├── config["timeout_seconds"] = 10..600
  ├── config["theme"] = "dark"|"light"
  ├── config["language"] = "ru"|"en"
  └── config.save()  → ~/.minlith/config.json
```

---

## 8. Многопоточность (src/workers/)

### 8.1 CalculationWorker

```python
class CalculationWorker(QThread):
    progress = pyqtSignal(int, int, str)   # (current, total, sample_name)
    finished = pyqtSignal(list)            # list[CalculationResult]
    error = pyqtSignal(str)                # error message

    PARALLEL_THRESHOLD = 10  # порог для параллельного расчёта

    def __init__(self, calculator: Calculator, samples: list[Sample], parent=None)
```

**Вход:** Calculator + list[Sample]
**Выход:** Сигнал finished с list[CalculationResult]

**Логика:**
```
ВХОД: Calculator, [Sample1, Sample2, ...SampleN]
  │
  ├── N < PARALLEL_THRESHOLD (10)?
  │     ├── Да → последовательный расчёт
  │     │     Для каждого sample:
  │     │       result = calculator.calculate_single(sample)
  │     │       progress.emit(i, N, sample.name)
  │     │
  │     └── Нет → параллельный расчёт (ProcessPoolExecutor)
  │           batch_size = cpu_count() * 2
  │           Разбиение на батчи
  │           ProcessPoolExecutor(max_workers=cpu_count())
  │           for batch in batches:
  │             futures = [pool.submit(_calc_single, (sample_dict, config_dict)) for ...]
  │             for future in as_completed(futures):
  │               name, result_dict, error = future.result()
  │               progress.emit(i, N, name)
  │
  └── finished.emit(results)  → list[CalculationResult]
```

### 8.2 _calc_single() — функция для ProcessPool

```python
def _calc_single(args: tuple) -> tuple[str, dict | None, str | None]
```

**ВХОД:** `(sample_dict, config_dict)` — сериализованные данные
**ВЫХОД:** `(sample_name, result_dict_or_None, error_or_None)`

**Причина:** Функция должна быть picklable для multiprocessing.

---

## 9. Конфигурация (src/utils/)

### 9.1 ConfigManager

```python
class ConfigManager:
    def __init__(self, path: Path | None = None)
```

**Путь по умолчанию:** `~/.minlith/config.json`

**Методы:**
```python
get(key: str, default: Any = None) -> Any      # Чтение
set(key: str, value: Any) -> None               # Запись (без сохранения)
save() -> None                                  # Запись на диск
add_recent_file(path: str) -> None              # Добавить в последние
reset() -> None                                 # Сброс (сохраняет recent_files)
export_settings(path: Path) -> None             # Экспорт в JSON
import_settings(path: Path) -> None             # Импорт из JSON
get_all() -> dict                               # Все настройки
```

**Дефолты:**
```python
DEFAULT_CONFIG = {
    "molar_mass_source": "iupac",
    "sum_tolerance": [98.0, 102.0],
    "warn_negative": True,
    "auto_correct_sum": False,
    "decimal_places": 2,
    "timeout_seconds": 120,
    "theme": "dark",
    "language": "ru",
    "recent_files": [],
    "max_recent": 10,
}
```

---

## 10. Логирование (src/utils/logger.py)

### 10.1 Настройка

```python
# Консоль: INFO уровень
# Файл: ~/.minlith/logs/minlith.log — DEBUG уровень
# Ротация: 5 MB, 3 бэкапа
# GUI: GUILogHandler → LogWidget (буфер 5000 записей)
```

### 10.2 Формат логов

```
[2026-07-23 10:30:15] [INFO] src.core.calculator: Рассчёт T-O2 → TYPE_5
[2026-07-23 10:30:15] [WARNING] src.core.validation: Сумма 97.5% ниже 98-102%
[2026-07-23 10:30:16] [ERROR] src.io.excel: Файл не найден: data.xlsx
```

---

## 11. CLI — полные примеры

### 11.1 calculate

```bash
# Простой расчёт
python -m src calculate data.xlsx
# ВХОД: data.xlsx (1+ образцов)
# ВЫХОД: minlith_results.xlsx

# С указанием формата
python -m src calculate data.xlsx --format csv
# ВЫХОД: minlith_results.csv

# Несколько файлов
python -m src calculate data1.xlsx data2.csv -o combined.xlsx
# ВЫХОД: combined.xlsx (все образцы из обоих файлов)

# Без кэша
python -m src calculate data.xlsx --no-cache
```

**Внутренний вызов:**
```
cmd_calculate(args)
  │
  ├── args.input = ["data.xlsx"]
  ├── args.output = None → "minlith_results.xlsx"
  ├── args.format = None → определяется по расширению
  ├── args.no_cache = False
  │
  ├── cache = ResultCache()
  │
  ├── Для каждого input_path:
  │     ├── cache.get(path) → cached?
  │     │     ├── Да (и не --no-cache) → десериализация в CalculationResult
  │     │     └── Нет → полный расчёт
  │     │
  │     ├── Загрузка: load_samples(path) | read_csv(path) | load_samples_from_zip(path)
  │     │
  │     ├── Для каждого sample:
  │     │     result = Calculator().calculate_single(sample)
  │     │     repo.save_result(result)
  │     │
  │     └── cache.put(path, results)
  │
  ├── Экспорт:
  │     fmt == "xlsx" → save_results(path, results)
  │     fmt == "csv" → save_results_csv(path, results)
  │     fmt == "json" → save_results_json(path, results)
  │     fmt == "pdf" → PDFGenerator(results).generate(path)
  │     fmt == "docx" → WordGenerator(results).generate(path)
  │     fmt == "html" → HTMLGenerator(results).generate(path)
  │
  └── print("Экспортировано {N} результатов в {path}")
```

### 11.2 info

```bash
python -m src info data.xlsx
# ВХОД: data.xlsx
# ВЫХОД: количество образцов, названия, суммы оксидов
```

### 11.3 validate

```bash
python -m src validate data.xlsx
# ВХОД: data.xlsx
# ВЫХОД: OK / предупреждения по каждому образцу
```

### 11.4 chart

```bash
python -m src chart data.xlsx --type tas -o chart.png
# ВХОД: data.xlsx, тип=tas
# ВЫХОД: chart.png

python -m src chart data.xlsx --type harker --interactive
# ВХОД: data.xlsx, тип=harker
# ВЫХОД: harker.html (Plotly интерактивный)
```

### 11.5 report

```bash
python -m src report data.xlsx --template standard -o report.pdf
# ВХОД: data.xlsx, шаблон=standard
# ВЫХОД: report.pdf
```

### 11.6 backup

```bash
# Создание резервной копии БД
python -m src backup
# ВЫХОД: ~/.minlith/backups/minlith_backup_YYYYMMDD_HHMMSS.db

# С указанием пути
python -m src backup -o /path/to/backup.db
```

### 11.7 export-db

```bash
# Экспорт БД в JSON
python -m src export-db
# ВЫХОД: minlith_export.json

# С указанием пути
python -m src export-db -o export.json
```

### 11.8 import-db

```bash
# Импорт JSON в БД
python -m src import-db export.json
# ВХОД: export.json
# ВЫХОД: данные загружены в БД
```

### 11.9 Глобальные флаги CLI

```bash
# Подробный вывод
python -m src calculate data.xlsx --verbose

# Таймаут (секунды)
python -m src calculate data.xlsx --timeout 300

# Путь к конфигу
python -m src calculate data.xlsx --config /path/to/config.json
```

---

## 12. Ошибки

| Модуль | Ошибка | Сообщение | Действие |
|---|---|---|---|
| excel.py | Файл не найден | "Файл не найден: {path}" | Пропуск файла |
| excel.py | Неверный формат | "Неподдерживаемый формат: {ext}" | Пропуск файла |
| csv_handler.py | Ошибка чтения | "Ошибка чтения CSV: {error}" | Пропуск файла |
| zip_handler.py | Не ZIP | "Not a valid ZIP file" | Ошибка |
| calculator.py | Division by zero | Fallback k1=1e-10 | Продолжение |
| calculator.py | F вне диапазона | "F must be between 0 and 1" | ValueError |
| coefficients.py | F вне диапазона | "F must be between 0 and 1" | ValueError |
| repository.py | Ошибка БД | "Ошибка сохранения: {error}" | Rollback |
| cache.py | Повреждён кэш | Удаление записи | Пересчёт |
| pdf_generator.py | Ошибка генерации | "Ошибка PDF: {error}" | Исключение |
| word_generator.py | Ошибка генерации | "Ошибка Word: {error}" | Исключение |

---

## 13. Портативная сборка

### 13.1 minlith.spec

```python
# PyInstaller spec file
# Расположение: корень проекта (minlith.spec)

a = Analysis(
    ['src/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('src/data', 'src/data')],
    hiddenimports=[...],
    ...
)
```

### 13.2 Сборка

```bash
# Полная сборка
pyinstaller minlith.spec

# Результат: dist/minlith/
dist/minlith/
├── minlith.exe          # Главный исполняемый файл
├── src/                 # Модули Python
├── _internal/           # Зависимости
└── ...
```

### 13.3 Использование

```bash
# Запуск из папки сборки
dist/minlith/minlith.exe calculate data.xlsx
dist/minlith/minlith.exe chart data.xlsx --type tas
dist/minlith/minlith.exe report data.xlsx -o report.pdf
```
