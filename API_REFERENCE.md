# API REFERENCE
# Публичный интерфейс MINLITH Modern

**Версия:** 1.0
**Дата:** 2026-07-17
**Статус:** Проектный (уточняется по мере реализации)

---

## 1. ОБЩИЕ ПРИНЦИПЫ

### 1.1. Импорты

```python
# Основной движок
from minlith.core.models import OxideComposition, CalculationResult
from minlith.core.calculator import Calculator

# Ввод-вывод
from minlith.io.excel_reader import ExcelReader
from minlith.io.excel_writer import ExcelWriter

# База данных
from minlith.database.repository import SampleRepository

# Диаграммы
from minlith.charts.built_in.bar_chart import BarChart

# Отчёты
from minlith.reports.pdf_generator import PDFGenerator
```

### 1.2. Типизация

Все публичные функции и методы типизированы (PEP 484).
Frozen dataclasses для неизменяемых данных.

### 1.3. Исключения

| Исключение | Условие | Обработка |
|-----------|---------|-----------|
| `ValidationError` | Некорректные входные данные | QMessageBox + подсветка |
| `CalculationError` | Ошибка в расчёте одного образца | Пропустить, записать в лог |
| `IOError` | Файл занят/не найден | Retry + QMessageBox |
| `ConfigError` | Некорректные настройки | Загрузить defaults |

---

## 2. CORE — РАСЧЁТНЫЙ ДВИЖОК

### 2.1. Модели данных

#### `OxideComposition`

```python
@dataclass(frozen=True)
class OxideComposition:
    sio2: float
    tio2: float
    al2o3: float
    fe2o3: float
    feo: float
    mgo: float
    cao: float
    na2o: float
    k2o: float
    p2o5: float
    mno: float = 0.0
    c: float = 0.0
    so3: float = 0.0
    f: float = 0.0
    cl: float = 0.0
    s: float = 0.0
    co2: float = 0.0
    so: float = 0.0

    def sum(self) -> float: ...
    def to_array(self) -> np.ndarray: ...
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

#### `FormulaUnits`

```python
@dataclass(frozen=True)
class FormulaUnits:
    sio2: float      # Si°
    tio2: float      # Ti°
    al2o3: float     # Al°
    fe2o3: float     # Fe3+°
    feo: float       # Fe2+°
    mgo: float       # Mg°
    cao: float       # Ca°
    na2o: float      # Na°
    k2o: float       # K°
    p2o5: float      # P°
    mno: float       # Mn°
    c: float
    so3: float
    f: float
    cl: float
    s: float
    co2: float
    so: float
    cao_corrected: float
    na2o_corrected: float
    fe_total: float
    fe1: float
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

    # Производные группы
    fsp: float = 0.0      # Полевые шпаты
    pel: float = 0.0       # Глинистые
    pel_fsp: float = 0.0    # Глинистые + полевые
    carsd: float = 0.0     # Карбонаты
    ill_kn: float = 0.0    # Ill + Kn
    chl_mm_srp: float = 0.0 # Chl + Mm + Srp

    def to_weight_percent(self, weights: MineralWeights) -> MineralComposition: ...
    def sum_formula_units(self) -> float: ...
    def sum_weight_percent(self, weights: MineralWeights) -> float: ...
```

**Примечание:** `pl = ab + an`, `fsp = ab + an + or_`, `pel = ill + chl + kn + mm + gb` и т.д.

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
    debug_trace: Optional[dict] = None
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
    def __init__(self, config: Optional[CalculationConfig] = None): ...

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

    def calculate_vectorized(
        self,
        samples: list[Sample]
    ) -> list[CalculationResult]: ...
```

**Пример:**
```python
from minlith.core.calculator import Calculator
from minlith.core.models import Sample

calc = Calculator()

samples = [
    Sample(name="БК-1", composition=comp1),
    Sample(name="T-O2", composition=comp2),
]

results = calc.calculate(samples, debug=True)

for r in results:
    print(f"{r.sample_name}: Type {r.rock_type}")
    print(f"  Ab: {r.minerals_weight.ab:.2f}%")
    print(f"  Q:  {r.minerals_weight.q:.2f}%")
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
    batch_size: Union[int, str] = "auto"     # int или "auto"
```

---

### 2.3. DebugTrace

#### `DebugTraceCollector`

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

**Пример вывода:**
```
Шаг 5.1: Ab = Na° = 151.66
Шаг 5.2: Si1 = Si° - 6*Ab = 7827.04
Шаг 5.3: Or = K° = 366.24
Шаг 5.4: An = (Si1 - 6*Or)/2 = 3913.52
Шаг 5.5: Gb = Al1 - Or - An = -1769.18  ⚠️ < 0!
Шаг 5.6: Переход к 3.2.1.
```

---

### 2.4. Validation

#### `validate_sample`

```python
def validate_sample(
    composition: OxideComposition,
    config: ValidationConfig
) -> tuple[bool, list[str]]:
    """
    Возвращает: (is_valid, warnings)
    """
```

**Проверки:**
- Сумма в диапазоне [98, 102]
- Нет отрицательных значений
- Нет NaN / inf
- Обязательные оксиды присутствуют (SiO2, Al2O3, ...)

---

## 3. IO — ВВОД/ВЫВОД

### 3.1. ExcelReader

```python
class ExcelReader:
    """Чтение Excel-файлов с автоматическим определением формата."""

    def __init__(self, aliases: Optional[dict] = None): ...

    def read(
        self,
        path: Path,
        sheet_name: Optional[str] = None,
        format_hint: Optional[str] = None   # "auto" | "classic" | "transposed"
    ) -> list[Sample]: ...

    def read_open_file(self, path: Path) -> list[Sample]:
        """Читает файл, открытый в Excel (read_only)."""
        ...

    def preview(self, path: Path, max_rows: int = 10) -> pd.DataFrame: ...

    def detect_format(self, path: Path) -> str:
        """Возвращает 'classic' или 'transposed'."""
        ...
```

**Пример:**
```python
reader = ExcelReader()
samples = reader.read(Path("data.xlsx"))

for s in samples:
    print(f"{s.name}: SiO2={s.composition.sio2}%")
```

---

### 3.2. ExcelWriter

```python
class ExcelWriter:
    """Запись результатов в Excel."""

    def write_results(
        self,
        results: list[CalculationResult],
        path: Path,
        mode: str = "new_file",     # "new_file" | "new_sheet" | "in_place"
        sheet_name: str = "Результаты",
        sections: Optional[list[str]] = None
    ): ...

    def write_combined(
        self,
        all_results: dict[str, list[CalculationResult]],  # filename -> results
        path: Path
    ): ...
```

**Режимы:**
- `new_file` — создать новый файл
- `new_sheet` — добавить лист в существующий (копия)
- `in_place` — добавить лист в исходный файл (копия)

---

### 3.3. LegacyImport

```python
class LegacyImport:
    """Импорт из старого MINLITH1.xlsx."""

    def read_legacy(self, path: Path) -> list[Sample]: ...
```

Читает лист "ИСХ ДАННЫЕ" и возвращает список Sample для пересчёта.

---

## 4. DATABASE — БАЗА ДАННЫХ

### 4.1. Engine

```python
from minlith.database.engine import get_engine, get_session

engine = get_engine(db_path: Optional[Path] = None)
# По умолчанию: %APPDATA%/MINLITH/minlith.db
```

---

### 4.2. Repository

#### `SampleRepository`

```python
class SampleRepository:
    def __init__(self, session: Session): ...

    def create(self, sample: Sample) -> int: ...
    def get_by_id(self, id: int) -> Optional[SampleDB]: ...
    def get_by_name(self, name: str) -> list[SampleDB]: ...
    def search(self, query: str) -> list[SampleDB]: ...
    def list_all(self, limit: int = 100, offset: int = 0) -> list[SampleDB]: ...
    def delete(self, id: int) -> bool: ...
```

#### `CalculationRepository`

```python
class CalculationRepository:
    def __init__(self, session: Session): ...

    def save(self, result: CalculationResult) -> int: ...
    def get_by_sample(self, sample_id: int) -> list[CalculationDB]: ...
    def get_latest(self, sample_id: int) -> Optional[CalculationDB]: ...
    def invalidate_by_version(self, version_hash: str): ...
    def get_invalid(self) -> list[CalculationDB]: ...
```

---

### 4.3. VersionTracker

```python
class VersionTracker:
    """Отслеживание версий алгоритма."""

    @staticmethod
    def compute_hash(source_file: Path) -> str:
        """SHA-256 от исходного кода types_logic.py."""
        ...

    @staticmethod
    def get_current_version() -> str:
        """Возвращает '1.11.5F' из __version__."""
        ...

    def check_calculations(self) -> tuple[int, int]:
        """
        Возвращает: (valid_count, invalid_count)
        Предлагает пересчитать invalid.
        """
        ...
```

---

## 5. CHARTS — ДИАГРАММЫ

### 5.1. Base

```python
from abc import ABC, abstractmethod
from matplotlib.figure import Figure

class ChartPlugin(ABC):
    @abstractmethod
    def get_name(self) -> str: ...

    @abstractmethod
    def get_description(self) -> str: ...

    @property
    @abstractmethod
    def requires_minerals(self) -> bool: ...

    @property
    @abstractmethod
    def requires_oxides(self) -> bool: ...

    @abstractmethod
    def render(
        self,
        data: ChartData,
        engine: str = "matplotlib",  # "matplotlib" | "plotly"
        **kwargs
    ) -> Figure: ...

    @abstractmethod
    def export(
        self,
        data: ChartData,
        path: Path,
        format: str = "png",  # "png" | "svg" | "pdf"
        **kwargs
    ): ...
```

---

### 5.2. Built-in Charts

```python
from minlith.charts.built_in.bar_chart import BarChart
from minlith.charts.built_in.pie_chart import PieChart
from minlith.charts.built_in.qapf import QAPFChart
from minlith.charts.built_in.acnk import ACNKChart
from minlith.charts.built_in.afm import AFMChart
from minlith.charts.built_in.tas import TASChart
```

**Пример:**
```python
chart = BarChart()
fig = chart.render(data, engine="matplotlib")
fig.savefig("output.png", dpi=150)
```

---

### 5.3. Custom Charts

```python
from minlith.charts.base import ChartPlugin

class MyScatterChart(ChartPlugin):
    def get_name(self) -> str:
        return "Мой scatter"

    def render(self, data, engine="matplotlib", **kwargs):
        # Реализация
        ...

# Сохранить в charts/custom/my_scatter.py
# Автоподхват при старте
```

---

## 6. REPORTS — ОТЧЁТЫ

### 6.1. TemplateBuilder

```python
class TemplateBuilder:
    """Конструктор отчётов drag-and-drop."""

    def __init__(self): ...

    def add_block(self, block: ReportBlock, position: int = -1): ...
    def remove_block(self, position: int): ...
    def move_block(self, from_pos: int, to_pos: int): ...
    def configure_block(self, position: int, config: dict): ...

    def save_template(self, name: str): ...
    def load_template(self, name: str) -> ReportTemplate: ...

    def generate(
        self,
        results: list[CalculationResult],
        format: str = "pdf"  # "pdf" | "docx" | "html"
    ) -> Path: ...
```

### 6.2. ReportBlock

```python
@dataclass
class ReportBlock:
    type: str  # "mineral_table" | "chart" | "parameters" | 
               # "defect" | "description"
    config: dict = field(default_factory=dict)
```

---

## 7. GUI — ПОЛЬЗОВАТЕЛЬСКИЙ ИНТЕРФЕЙС

### 7.1. MainWindow

```python
class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self): ...

    def show_page(self, page_name: str): ...
    def show_welcome(self): ...
    def show_files(self): ...
    def show_settings(self): ...
    def show_results(self): ...
    def show_charts(self): ...
    def show_compare(self): ...
    def show_database(self): ...
    def show_logs(self): ...
```

### 7.2. CalculationDialog

```python
class CalculationDialog(QDialog):
    """Диалог расчёта с прогресс-баром."""

    def __init__(self, worker: CalculationWorker): ...

    def start(self): ...
    def cancel(self): ...

    # Сигналы
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    cancelled = pyqtSignal(int)
```

### 7.3. Pages

```python
# src/gui/pages/
WelcomePage      # Приветствие, быстрый старт
FilesPage        # Drag-drop, превью, список файлов
SettingsPage     # Настройки расчёта, отображения, путей
ResultsPage      # Таблица результатов, фильтры, экспорт
ChartsPage       # Диаграммы, выбор образцов, настройки
ComparePage      # Сравнение результатов, статистика
DatabasePage     # История расчётов, поиск, фильтры
LogsPage         # Логи, фильтр по уровню, поиск
```

---

## 8. WORKERS — ПАРАЛЛЕЛЬНОСТЬ

### 8.1. CalculationWorker

```python
class CalculationWorker(QObject):
    """QThread + ProcessPoolExecutor."""

    progress = pyqtSignal(int, str)      # (percent, message)
    sample_done = pyqtSignal(int, object)  # (index, result)
    finished = pyqtSignal(list)           # [CalculationResult, ...]
    error = pyqtSignal(str, Exception)
    cancelled = pyqtSignal(int)           # processed_count

    def __init__(
        self,
        samples: list[Sample],
        config: CalculationConfig,
        batch_size: Union[int, str] = "auto"
    ): ...

    def run(self): ...
    def cancel(self): ...
```

---

## 9. UTILS — УТИЛИТЫ

### 9.1. Config

```python
class ConfigManager:
    """Управление настройками JSON."""

    def __init__(self, path: Optional[Path] = None):
        # По умолчанию: %APPDATA%/MINLITH/settings.json
        ...

    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any): ...
    def save(self): ...
    def load(self): ...
    def export(self, path: Path): ...
    def import_(self, path: Path): ...
    def reset_to_defaults(self): ...
```

### 9.2. Logger

```python
class GUILogHandler(logging.Handler):
    """Handler для вывода логов в GUI."""

    def __init__(self, widget: QTextEdit): ...
    def emit(self, record: logging.LogRecord): ...

def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    gui_handler: Optional[GUILogHandler] = None
) -> logging.Logger: ...
```

---

## 10. ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### 10.1. Быстрый старт (CLI)

```python
from pathlib import Path
from minlith.io.excel_reader import ExcelReader
from minlith.core.calculator import Calculator
from minlith.io.excel_writer import ExcelWriter

# Чтение
reader = ExcelReader()
samples = reader.read(Path("input.xlsx"))

# Расчёт
calc = Calculator()
results = calc.calculate(samples)

# Запись
writer = ExcelWriter()
writer.write_results(results, Path("output.xlsx"))
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
from minlith.database.engine import get_session
from minlith.database.repository import CalculationRepository

session = get_session()
repo = CalculationRepository(session)

for r in results:
    repo.save(r)

# Проверка устаревших
invalid = repo.get_invalid()
print(f"Устаревших расчётов: {len(invalid)}")
```

### 10.4. С диаграммой

```python
from minlith.charts.built_in.bar_chart import BarChart

chart = BarChart()
fig = chart.render(results, engine="matplotlib")
fig.savefig("minerals.png", dpi=150)
```

---

## 11. ИЗМЕНЕНИЯ API

| Версия | Изменение |
|--------|-----------|
| 1.0 | Начальная версия |

---

## 12. ЗАМЕЧАНИЯ

- Все `float` — `float64` (numpy) для точности
- Все пути — `pathlib.Path`
- Все даты — `datetime.datetime` (timezone-aware)
- Все проценты — 0-100 (не 0-1)
- Все вес.% — округление только на выводе
