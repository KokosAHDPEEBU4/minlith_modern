# API REFERENCE
# Публичный интерфейс MINLITH Modern

**Версия:** 2.0
**Дата:** 2026-07-24
**Статус:** Актуальный (v0.7.0)

---

## 1. ОБЩИЕ ПРИНЦИПЫ

### 1.1. Импорты

```python
# Основной движок
from src.core.models import OxideComposition, Sample, CalculationResult, CalculationConfig
from src.core.calculator import Calculator

# Ввод-вывод
from src.io.excel import read_excel, write_excel
from src.io.csv_handler import read_csv, write_csv
from src.io.xrf_importer import read_xrf

# База данных
from src.database.repository import SampleRepository, CalculationRepository
from src.database.engine import get_engine, get_session

# Диаграммы
from src.charts.built_in.bar_chart import BarChart

# Отчёты
from src.reports.pdf_generator import PDFGenerator
from src.reports.latex_exporter import LaTeXExporter
from src.reports.template_builder import TemplateBuilder

# Калибровка
from src.core.calibrator import Calibrator, save_calibration_config, load_calibration_config

# Аномалии
from src.core.anomaly_detector import AnomalyDetector

# Объяснения
from src.core.explainer import Explainer
```

### 1.2. Типизация

Все публичные функции и методы типизированы (PEP 484).
Frozen dataclasses для неизменяемых данных.

### 1.3. Исключения

| Исключение | Условие | Обработка |
|-----------|---------|-----------|
| `CalculationTimeoutError` | Расчёт превысил лимит | Пропустить образец, лог |
| `ValueError` | Некорректные входные данные | Пропустить, записать в лог |

---

## 2. CORE — РАСЧЁТНЫЙ ДВИЖОК

### 2.1. Модели данных

#### `OxideComposition`

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

    def sum(self) -> float: ...
    def to_array(self) -> np.ndarray: ...  # shape (18,)
    @classmethod
    def from_dict(cls, data: dict[str, float]) -> OxideComposition: ...
```

**Пример:**
```python
comp = OxideComposition(
    sio2=52.31, tio2=0.66, al2o3=16.46,
    fe2o3=0.92, feo=4.43, mgo=0.11,
    cao=6.8, na2o=8.08, k2o=4.26,
    p2o5=1.85, mno=0.12, so3=3.54, f=0.41
)
print(comp.sum())  # 99.95
```

---

#### `Sample`

```python
@dataclass(frozen=True)
class Sample:
    name: str
    composition: OxideComposition
```

---

#### `FormulaUnits`

```python
@dataclass(frozen=True)
class FormulaUnits:
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
    cao_corrected: float = 0.0
    na2o_corrected: float = 0.0
    fe_total: float = 0.0
    fe1: float = 0.0
```

**Примечание:** Поля `*_corrected` содержат значения после вычета апатита, флюорита, галита.

---

#### `AdaptiveCoefficients`

```python
@dataclass(frozen=True)
class AdaptiveCoefficients:
    k1: float   # Mg в хлорите
    k2: float   # Fe в хлорите
    k3: float   # Al в хлорите
    k4: float   # Si в хлорите
    F: float    # Fe3+/ΣFe
    A: float    # Al/(Al+Fe)

    @classmethod
    def from_F(cls, F: float, A: float,
               mass_source: str = "iupac") -> AdaptiveCoefficients: ...
```

**Пример:**
```python
coeffs = AdaptiveCoefficients.from_F(F=0.696, A=0.705)
print(coeffs.k1)  # 1.427
print(coeffs.k2)  # 3.008
print(coeffs.k3)  # 1.469
print(coeffs.k4)  # 2.627
```

---

#### `MineralComposition`

```python
@dataclass(frozen=True)
class MineralComposition:
    # Полевые шпаты
    ab: float = 0.0    # Альбит
    an: float = 0.0    # Анортит
    pl: float = 0.0    # Плагиоклаз (Ab+An)
    or_: float = 0.0   # Ортоклаз

    # Глинистые
    ill: float = 0.0   # Иллит
    chl: float = 0.0   # Хлорит
    kn: float = 0.0    # Каолинит
    mm: float = 0.0    # Монтмориллонит
    gb: float = 0.0    # Гиббсит

    # Карбонаты
    cc: float = 0.0    # Кальцит
    dl: float = 0.0    # Доломит
    ank: float = 0.0   # Анкерит
    rch: float = 0.0   # Родохрозит
    sd: float = 0.0    # Сидерит

    # Прочие
    q: float = 0.0     # Кварц
    ap: float = 0.0    # Апатит
    c: float = 0.0     # Углерод
    srp: float = 0.0   # Серпентин
    mst: float = 0.0   # Магнезит
    ht: float = 0.0    # Гематит
    prl: float = 0.0   # Пиролюзит
    pr: float = 0.0    # Пирит
    rt: float = 0.0    # Рутил
    hl: float = 0.0    # Галит
    gy: float = 0.0    # Гипс
    fl: float = 0.0    # Флюорит

    def sum_formula_units(self) -> float: ...
```

---

#### `CalculationResult`

```python
@dataclass(frozen=True)
class CalculationResult:
    sample_name: str
    input_composition: OxideComposition
    formula_units: FormulaUnits
    coefficients: AdaptiveCoefficients
    rock_type: RockType
    minerals_formula: MineralComposition   # в ф.е.
    minerals_weight: MineralComposition      # в вес.%
    defect: dict[str, float]               # остатки оксидов
    warnings: list[str]
    debug_trace: Optional[object] = None
    geo_params: Optional[object] = None    # GeoParameters (CIA, ICV, PIA, ASI, AI)
    anomalies: Optional[list] = None       # list[AnomalyHypothesis]
```

---

#### `RockType` (Enum)

```python
class RockType(IntEnum):
    TYPE_1 = 1   # Al <= 1.2Na + K
    TYPE_2 = 2   # Al <= 1.2Na + 3.25K
    TYPE_3 = 3   # Al <= 1.2Na + 3.25K + (Mg-0.5K*k3)/k1
    TYPE_4 = 4   # Al <= 5Na + 3.25K + (Mg-0.5K-2Na)*k3/k1
    TYPE_5 = 5   # Al > всё выше
```

---

### 2.2. Calculator

#### `Calculator`

```python
class Calculator:
    def __init__(
        self,
        config: Optional[CalculationConfig] = None,
        algorithm: Optional[MineralAlgorithm] = None,
    ): ...

    def calculate(
        self,
        samples: list[Sample],
        debug: bool = False
    ) -> list[CalculationResult]: ...

    def calculate_single(
        self,
        sample: Sample,
        debug: bool = False
    ) -> CalculationResult: ...
```

**Пример:**
```python
from src.core.calculator import Calculator
from src.core.models import Sample, OxideComposition

calc = Calculator()

comp = OxideComposition(
    sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
    mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45,
)
sample = Sample(name="T-O2", composition=comp)
result = calc.calculate_single(sample)

print(result.rock_type)          # RockType.TYPE_5
print(result.minerals_weight.ab) # 7.82
print(result.minerals_weight.q)  # 31.38
print(result.defect)             # oxide residuals
print(result.anomalies)          # list[AnomalyHypothesis]
```

---

#### `CalculationConfig`

```python
@dataclass
class CalculationConfig:
    molar_mass_source: str = "iupac"      # "iupac" | "minlith"
    custom_molar_masses: dict[str, float] = field(default_factory=dict)
    sum_tolerance: tuple[float, float] = (98.0, 102.0)
    warn_negative: bool = True
    auto_correct_sum: bool = False
    decimal_places: int = 2
    include_formula_units: bool = False
    include_defect: bool = True
    include_parameters: bool = True
    timeout_seconds: int = 120
    batch_size: int | str = "auto"
    calculation_engine: str = "geological_theory"  # см. движки ниже
```

**Движки расчёта (`calculation_engine`):**

| Значение | Класс | Как считает |
| --- | --- | --- |
| `excel_parity` | `ExcelParityAlgorithm` | «как в Excel» с корректными округлениями: те же формулы в float64 без пошаговых `ROUND` (дефолт приложения) |
| `excel_exact` | `ExcelExactAlgorithm` | «Excel 1:1»: формулы + VBA + пошаговые `ROUND`, включая накопление ошибки округления книги MINLITH |
| `geological_theory` | `GeologicalTheoryAlgorithm` | самостоятельный расчёт по геологической теории (файлы 00-07) |
| `python_rework` | — (плейсхолдер) | пользовательская переработка; пока fallback на теорию |

```python
from src.core.models import CalculationConfig
from src.core.calculator import Calculator

calc = Calculator(config=CalculationConfig(calculation_engine="excel_exact"))
```

> `AlgorithmInput` для `excel_exact` дополнительно несёт `oxide_wt: dict[str, float] | None` —
> исходные вес.% оксидов (ключи Excel: `"SiO2"`, `"TiO2"`, …), т.к. книга сама пересчитывает
> вес.% → ф.е. с `ROUND`. Без `oxide_wt` движок поднимает `ValueError`.

**Траектория веток (для графа разветвлений).** Движок `excel_parity` дополнительно
возвращает структурированный маршрут принятых решений:

```python
from src.core.excel_parity.runner import run_sample
from src.core.excel_parity.branches import BranchPath, BranchDecision

run = run_sample({"SiO2": 70.0, "Al2O3": 12.0, "Na2O": 3.0, "K2O": 6.0})
run.st0.coefficient_band      # "H5" | "J5" | "L5" | "H12" | "J12" | "L12"
run.st0.type_conditions       # {"e20": .., "e21": .., "e22": .., "e24": .., "e25": ..}
path: BranchPath = run.path   # полоса, тип, подписи веток типа и VI этапа
path.labels()                 # ["band_H5", "rock_type_1", "t_52~53", "A"]
path.to_dict()                # {"labels": [...], "decisions": [{stage, name, condition, source, value}]}
```

`AlgorithmOutput.path: dict | None` — тот же маршрут на выходе `algorithm.compute`
(`Calculator.calculate_single(debug=True)` дополнительно пишет его в
`DebugTraceCollector` через `record_branch_path`). У других движков `path = None`.

В `CalculationResult` маршрут доступен как `CalculationResult.branch_path: dict | None`.
Для показа/экспорта — чистый модуль `src/core/branch_report.py`:

```python
from src.core.branch_report import describe_branch_path, format_branch_path_text

describe_branch_path(result.branch_path)
# [{"stage": "stage0", "stage_title": "Стадия 0", "name": "band_H5",
#   "condition": "0 < F < 0.21", "source": "G17"}, ...]
print(format_branch_path_text(result.branch_path, result.sample_name))
```

В GUI: страница «Результаты» → кнопка «Маршрут веток» (диалог
`src/gui/dialogs/branch_path_dialog.py`).

**Ручной выбор веток (override).** Каталог решений —
`src/core/excel_parity/branch_catalog.py` (`DECISIONS`, `find_decision`,
`branch_ids`, `catalog_to_dict`). Выбор задаётся `BranchOverrides` и
валидируется по каталогу:

```python
from src.core.models import CalculationConfig, OxideComposition, Sample
from src.core.calculator import Calculator

cfg = CalculationConfig(
    calculation_engine="excel_parity",
    branch_overrides={"rock_type": "3", "coefficient_band": "H12"},
)
result = Calculator(config=cfg).calculate_single(sample)
```

- `CalculationConfig.branch_overrides: dict[str, str]`, `forced_path: tuple[str, ...]`.
- `AlgorithmInput.overrides: BranchOverrides | None`, `Stage0.overrides`.
- `src/core/branch_overrides.py`: `BranchOverrides.choices/forced_path/get/is_empty/to_dict`,
  `validate_overrides()` (неизвестное решение/ветка или `overridable=False` → `ValueError`).
  Пустой выбор не меняет поведение.

---

### 2.3. Coefficients

```python
from src.core.coefficients import calculate_coefficients

coeff = calculate_coefficients(F=0.5, A=0.7)
# Returns AdaptiveCoefficients with k1, k2, k3, k4, F, A
```

Кэшируется через `@lru_cache(1024)`.

---

### 2.4. DebugTrace

```python
class DebugTraceCollector:
    def __init__(self, sample_name: str): ...

    def record(self, step: str, variable: str,
               value: float, comment: str = ""): ...

    def record_condition(self, step: str, condition: str,
                         result: bool, branch: str): ...

    def to_dict(self) -> dict: ...
    def to_text(self) -> str: ...
    def export_json(self, path: Path): ...
```

---

### 2.5. Validation

```python
def validate_sample(
    composition: OxideComposition,
    config: CalculationConfig
) -> tuple[bool, list[str]]:
    """
    Возвращает: (is_valid, warnings)
    """
```

**Проверки:**
- Сумма в диапазоне [98, 102]
- Нет отрицательных значений
- Нет NaN / inf

---

### 2.6. AnomalyDetector

```python
from src.core.anomaly_detector import AnomalyDetector

detector = AnomalyDetector()
anomalies = detector.analyze(result)  # CalculationResult -> list[AnomalyHypothesis]
```

**10 правил детекции:**
1. Гипс (SO3 > 5%)
2. Низкая сумма оксидов (< 98%)
3. Высокая сумма оксидов (> 102%)
4. Железистая порода (FeO + Fe2O3 > 15%)
5. Апатит (P2O5 > 2%)
6. Критический дефект (> 10%)
7. Карбонатная порода (CaO + MgO > 20%)
8. Аномальный полевой шпат (Ab + An + Or > 90%)
9. Фосфор (P2O5 > 0.5%)
10. Отрицательные минералы (Kn < 0 или Dl < 0)

---

### 2.7. Explainer

```python
from src.core.explainer import Explainer

explainer = Explainer()
text = explainer.explain(result)  # CalculationResult -> str (Russian)
```

Генерирует человекочитаемое объяснение процесса расчёта на русском языке.

---

## 3. IO — ВВОД/ВЫВОД

### 3.1. Excel

```python
from src.io.excel import read_excel, write_excel

# Чтение
samples = read_excel(Path("input.xlsx"), sheet_name=None)

# Запись результатов
write_excel(Path("output.xlsx"), results)
```

**Поддерживаемые форматы:**
- MINLITH original (ИСХ ДАННЫЕ стиль): строки 2-19 — оксиды
- Транспонированный (Копия ИД): колонки B+ — данные
- .xls (old Excel 97-2003) — через xlrd

---

### 3.2. CSV

```python
from src.io.csv_handler import read_csv, write_csv

# Чтение
samples = read_csv(Path("data.csv"), separator=None)  # автоопределение

# Запись
write_csv(Path("out.csv"), results, separator=";")
```

**Автоопределение:** разделитель (`;` или `,`), кодировка (`utf-8`, `cp1251`).

---

### 3.3. XRF Import

```python
from src.io.xrf_importer import read_xrf

samples = read_xrf(Path("spectrum.csv"))
```

**Поддерживаемые форматы:** Bruker, Panalytical, Rigaku (CSV/TXT).

---

## 4. DATABASE — БАЗА ДАННЫХ

### 4.1. Engine

```python
from src.database.engine import get_engine, get_session

engine = get_engine()  # %APPDATA%/MINLITH/minlith.db
session = get_session()
```

---

### 4.2. Repository

```python
from src.database.repository import SampleRepository, CalculationRepository

# Работа с образцами
repo = SampleRepository(session)
sample_id = repo.create(sample)
all_samples = repo.list_all()

# Работа с расчётами
calc_repo = CalculationRepository(session)
calc_repo.save(result)
latest = calc_repo.get_latest(sample_id)
```

---

## 5. CHARTS — ДИАГРАММЫ

### 5.1. Base

```python
from src.charts.base import ChartPlugin

class MyChart(ChartPlugin):
    def get_name(self) -> str: ...
    def get_description(self) -> str: ...
    @property
    def requires_minerals(self) -> bool: ...
    @property
    def requires_oxides(self) -> bool: ...
    def render(self, data, engine="matplotlib", **kwargs) -> Figure: ...
    def export(self, data, path, format="png", **kwargs): ...
```

---

### 5.2. Built-in Charts (15)

| Chart | Тип | Требует |
|-------|-----|---------|
| `BarChart` | Столбчатая | минералы |
| `PieChart` | Круговая | минералы |
| `DefectChart` | Дефект | оксиды |
| `QAPFChart` | QAPF треугольник | минералы |
| `TASChart` | TAS | оксиды |
| `ACNKChart` | A-CN-K | оксиды |
| `AFMChart` | A-F-M | оксиды |
| `HeatmapChart` | Тепловая карта | минералы |
| `RockTypeChart` | Тип породы | минералы |
| `FeldsparTriangle` | Полевые шпаты | минералы |
| `HarkerChart` | Харкера | оксиды |
| `SiO2K2OChart` | SiO2-K2O | оксиды |
| `BlandAltmanChart` | Bland-Altman | минералы |
| `CorrelationChart` | Корреляция | минералы |
| `KFChart` | k1-k4 vs F | коэффициенты |

```python
from src.charts.built_in.bar_chart import BarChart

chart = BarChart()
fig = chart.render(data, engine="matplotlib")
fig.savefig("minerals.png", dpi=150)
```

---

## 6. REPORTS — ОТЧЁТЫ

### 6.1. TemplateBuilder (5 шаблонов)

```python
from src.reports.template_builder import TemplateBuilder

builder = TemplateBuilder()
path = builder.generate(results, format="pdf")  # "pdf" | "docx" | "html"
```

| Шаблон | Назначение |
|--------|-----------|
| `brief` | Краткий отчёт (1 страница) |
| `standard` | Стандартный отчёт |
| `full` | Полный отчёт со всеми диаграммами |
| `core` | Отчёт по керну |
| `geochemical` | Геохимический паспорт |

---

### 6.2. PDF Generator

```python
from src.reports.pdf_generator import PDFGenerator

pdf = PDFGenerator()
pdf.generate(results, Path("report.pdf"), template="full")
```

---

### 6.3. LaTeX Exporter

```python
from src.reports.latex_exporter import LaTeXExporter

latex = LaTeXExporter()
latex.export_table(results, Path("table.tex"), table_type="minerals")
```

Генерирует публикационные таблицы с `booktabs`, `\textsubscript`.

---

## 7. CALIBRATION — КАЛИБРОВКА

### 7.1. Calibrator

```python
from src.core.calibrator import Calibrator

sample, expected = read_expected_from_excel(Path("MINLITH1.xlsx"))
calibrator = Calibrator(sample, expected)
result = calibrator.calibrate(maxiter=1000, seed=42)

print(result.rmse_before)  # 66.15
print(result.rmse_after)   # 0.09
print(result.params)       # calibrated parameters
print(result.report)       # human-readable report
```

### 7.2. Save/Load Config

```python
from src.core.calibrator import save_calibration_config, load_calibration_config

save_calibration_config(result.params, Path("calibration_config.json"))
params = load_calibration_config(Path("calibration_config.json"))
```

### 7.3. CLI

```bash
python calibrate.py --input MINLITH1.xlsx --output calibration_config.json --maxiter 1000
```

---

## 8. CACHE — КЭШИРОВАНИЕ

```python
from src.utils.cache import ResultCache

cache = ResultCache(cache_dir=Path("~/.minlith/cache"), ttl_seconds=7*24*3600)

# Проверка кэша
cached = cache.get(file_path)

# Сохранение
cache.put(file_path, results)

# Инвалидация
cache.invalidate(file_path)
cache.clear()  # удалить всё

# Статистика
stats = cache.stats()  # {"entries": 5, "cache_dir": "...", "ttl_seconds": 604800}

# Очистка устаревших
removed = cache.cleanup_expired()
```

---

## 9. CLI — КОМАНДЫ

```bash
# Расчёт
python -m src calculate input.xlsx -o results.xlsx

# С подробным выводом
python -m src calculate input.xlsx -V --timeout 300

# Диаграмма
python -m src chart input.xlsx --type tas -o chart.png

# Отчёт
python -m src report input.xlsx --template full -o report.pdf

# Резервная копия
python -m src backup -o backups/

# Экспорт БД
python -m src export-db -o export.json

# Валидация
python -m src validate input.xlsx

# Список диаграмм
python -m src list-charts

# Список шаблонов
python -m src list-templates
```

---

## 10. ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### 10.1. Быстрый старт

```python
from src.core.models import OxideComposition, Sample
from src.core.calculator import Calculator
from src.io.excel import read_excel, write_excel
from pathlib import Path

# Чтение
samples = read_excel(Path("input.xlsx"))

# Расчёт
calc = Calculator()
results = calc.calculate(samples)

# Запись
write_excel(Path("output.xlsx"), results)
```

### 10.2. С отладкой

```python
results = calc.calculate(samples, debug=True)

for r in results:
    if r.debug_trace:
        print(r.debug_trace.to_text())
        r.debug_trace.export_json(Path(f"debug_{r.sample_name}.json"))
```

### 10.3. С базой данных

```python
from src.database.engine import get_session
from src.database.repository import CalculationRepository

session = get_session()
repo = CalculationRepository(session)

for r in results:
    repo.save(r)
```

### 10.4. С калибровкой

```python
from src.core.calibrator import Calibrator, save_calibration_config

sample, expected = read_expected_from_excel(Path("MINLITH1.xlsx"))
calibrator = Calibrator(sample, expected)
result = calibrator.calibrate(maxiter=1000)
save_calibration_config(result.params, Path("calibration_config.json"))
```

### 10.5. С аномалиями

```python
from src.core.anomaly_detector import AnomalyDetector

detector = AnomalyDetector()
for r in results:
    anomalies = detector.analyze(r)
    for a in anomalies:
        print(f"⚠️ {a.rule}: {a.message}")
```

---

## 11. ИЗМЕНЕНИЯ API

| Версия | Изменение |
|--------|-----------|
| 2.0 | Импорты `src.core.*`, калибровка, аномалии, XRF, LaTeX |
| 1.0 | Начальная версия |

---

## 12. ЗАМЕЧАНИЯ

- Все `float` — `float64` (numpy) для точности
- Все пути — `pathlib.Path`
- Все даты — `datetime.datetime` (timezone-aware)
- Все проценты — 0-100 (не 0-1)
- Все вес.% — округление только на выводе
- Отрицательные минералы (Kn, Dl) — валидные артефакты
