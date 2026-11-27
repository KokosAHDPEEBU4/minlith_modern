# ТЗ: граф разветвлений MINLITH — визуализация маршрута и ручной выбор ветки

**Версия:** 1.0
**Дата:** 2026-09-21
**Адресат:** ИИ-исполнитель (не знаком с проектом), а также ревьюер (человек), который будет проверять этапы.
**Статус:** к реализации.

> Этот документ самодостаточен: всё, что нужно знать о проекте, собрано в
> разделах 1–2 и приложении 9. Выполнять **по этапам** (раздел 5), после каждого
> этапа — прогон тестов/линтера и обновление документации (см. раздел 6).

---

## 0. Как работать с этим ТЗ (обязательные правила исполнителя)

1. **Только добавлять, ничего не удалять.** Не удалять рабочий код, тесты,
   файлы. Неиспользуемое — не трогать. Перемещение отслеживаемых файлов — через
   `git mv`.
2. **Дефолтное поведение не меняется.** Все текущие тесты и паритет должны
   остаться зелёными. Новая функциональность включается только явно (override,
   открытие страницы).
3. **Документация не отстаёт от кода** (правило `AGENTS.md`): любое изменение
   кода сопровождается правкой md-файлов в том же этапе. Числа (кол-во тестов)
   брать из фактического прогона `pytest`, а не из памяти.
4. **Не коммитить** без явной просьбы человека. Работать в рабочем дереве.
5. **После каждого этапа** запускать:
   ```bash
   # из папки minlith_modern/
   python -m pytest -q
   python -m ruff check src/ tests/
   ```
   и прикладывать в отчёте: сколько тестов прошло/упало, вывод ruff.
6. **Стиль кода:** следовать существующему. Не добавлять комментарии-очевидности;
   комментарии — только там, где логика неочевидна (как в существующем коде).
7. **Платформа:** Windows, PowerShell; Python 3.14; PyQt6; pytest.
8. Если что-то в ТЗ противоречит фактическому коду — **сначала зафиксировать
   расхождение в отчёте**, потом принимать решение.

---

## 1. Что это за проект (минимум контекста)

`minlith_modern/` — Python-приложение MINLITH (нормативный минералогический
расчёт). Есть расчётное ядро (`src/core/`), PyQt6-GUI (`src/gui/`), диаграммы
(`src/charts/`), отчёты (`src/reports/`), тесты (`tests/`).

**Расчётные движки** задаются конфигом `calculation_engine`:

| Значение | Класс | Суть |
|---|---|---|
| `excel_parity` (по умолчанию) | `ExcelParityAlgorithm` | точный порт алгоритма Excel **без** пошаговых `ROUND` (float64) |
| `excel_exact` | `ExcelExactAlgorithm` | полная 1:1 копия Excel (`excel_port(rounding=True)`) |
| `geological_theory` | `GeologicalTheoryAlgorithm` | самостоятельная теория |
| `python_rework` | — (плейсхолдер) | fallback на теорию |

Нас интересует **`excel_parity`**: его алгоритм — большое дерево решений
(тип породы → полоса коэффициентов → внутренние ветви типа → этап VI). Движок
уже умеет возвращать **маршрут веток** (какие решения приняты). Задача ТЗ:
(1) показать этот маршрут как граф, (2) дать пользователю **выбирать ветку
вручную** и пересчитывать.

**Оракул для сверки:** `excel_port.run_sample(oxides, rounding=False)` — полный
порт формул+VBA. Инвариант: `excel_parity` по умолчанию совпадает с ним (на
текущих тестах и решётке). **Этот инвариант нельзя ломать.**

---

## 2. Что уже готово (не изобретать заново)

| Что | Где |
|---|---|
| Структура маршрута: `BranchDecision`, `BranchPath` | `src/core/excel_parity/branches.py` |
| Каталоги условий: `COEFFICIENT_BAND_INFO`, `ROCK_TYPE_INFO`, `STAGE_VI_INFO`, `TYPE_BRANCH_INFO` | `src/core/excel_parity/branches.py` |
| Сборка маршрута образца: `ExcelRun.path` (property) | `src/core/excel_parity/runner.py` |
| Маршрут на выходе движка: `AlgorithmOutput.path: dict \| None` | `src/core/algorithm.py` |
| Маршрут в результате: `CalculationResult.branch_path: dict \| None` | `src/core/models.py` |
| Форматирование маршрута (чистое, без Qt): `describe_branch_path`, `format_branch_path_text`, `branch_path_headers` | `src/core/branch_report.py` |
| Диалог «Маршрут веток» | `src/gui/dialogs/branch_path_dialog.py` |
| Кнопка «Маршрут веток» на странице результатов | `src/gui/pages/results_page.py` |
| Вход/выход алгоритма: `AlgorithmInput`, `AlgorithmOutput` | `src/core/algorithm.py` |
| Конфиг: `CalculationConfig`, `CALCULATION_ENGINES` | `src/core/models.py` |
| Фабрика движков: `Calculator._algorithm_for_engine`, `_build_algorithm_input` | `src/core/calculator.py` |
| Настройки приложения: `ConfigManager`, `DEFAULT_CONFIG` | `src/utils/config.py` |
| Стадия 0 (полоса, тип): `compute_stage0`, `coefficients`, `coefficient_band`, `classify`, `classify_conditions`, `Stage0` | `src/core/excel_parity/stage0.py` |
| Типы 1–5: `solve_type`, `type1..type45`, `TypeSolution` | `src/core/excel_parity/types.py` |
| Этап VI: `solve_stage_vi`, `StageVI` | `src/core/excel_parity/stage_vi.py` |
| GUI: главное окно, страницы, сайдбар | `src/gui/main_window.py` |
| Готовый селектор «чекбоксы + Все/Снять/Инверсия» | `SampleSelectorDialog` в `src/gui/pages/charts_page.py` |
| Спецификация интерактива диаграмм | `minlith_modern/docs/CHART_INTERACTIONS_SPEC.md` |
| Скрипт сверки с живым Excel | `scripts/verify_excel_parity.py` |
| Контекст-документ по графам | `docs/planning/BRANCH_GRAPH_SELECTION.md` |

**Важно про диаграммы.** Реестры диаграмм **позиционные** и проверяются на
«ровно 23»: `BUILTIN_CHARTS` (`src/charts/built_in/__init__.py`),
`BUILTIN_TYPE_IDS` + `SPECS` (`src/gui/widgets/chart_interactions.py`),
`BUILTIN_SIZE_IDS` + `STANDARDS` (`src/gui/widgets/chart_sizes.py`). Добавление
24-й диаграммы — это правка 5 мест + изменение проверок. **В этом ТЗ граф
делается отдельной GUI-страницей, а не через `ChartPlugin`** — чтобы не ломать
эти реестры.

**Навигация GUI (важно для этапа 4).** Страницы перечислены в
`main_window.py`: список `_page_names` (порядок = индексы), затем создание
страниц и `self._stack.addWidget(...)` в том же порядке, затем горячие клавиши
с **числовыми индексами** (`Ctrl+D` → 4 и т.п.). При добавлении страницы нужно
согласованно поправить все три места и индексы горячих клавиш.

---

## 3. Цель и объём (MoSCoW)

**MUST (обязательно для приёмки):**
1. Статический **каталог решений** (вершины и ветки) для трёх уровней: полоса
   коэффициентов, тип породы, этап VI. Плюс отображение внутренних веток типа
   как подписей маршрута.
2. **Визуализация маршрута**: дерево решений с подсветкой пройденного пути
   конкретного образца.
3. **Ручной выбор ветки** (override) для `rock_type`, `coefficient_band`,
   `stage_vi` с пересчётом и отображением, что ветка принудительная.
4. **Валидация** выбора (недопустимая ветка → понятная ошибка), экспорт
   маршрута/графа.

**SHOULD (желательно):**
5. Сравнение двух маршрутов (например, «авто» vs «принудительный») — таблица
   различий.
6. Override внутренних веток типа 3/4/5 (см. этап 6).

**COULD (если останется время):**
7. Экспорт интерактивного графа (Plotly/SVG).
8. Сохранение «сценариев» маршрутов в конфиг/файл (загрузка/выгрузка).

Критерий полноты: MUST+SHOULD выполнены, этап 7 (финализация) пройден.

---

## 4. Архитектура решения

```
                 branch_catalog.py           (этап 1)
             (статические решения/ветки)
                        │
        ┌───────────────┴────────────────┐
        ▼                                ▼
  Overrides (этап 2-3)              GUI-страница (этап 4)
  config → AlgorithmInput          дерево + маршрут + выбор
        → excel_parity                   │
        → path (BranchPath)  ───────────►│ подсветка/пересчёт
```

- **Каталог** (`branch_catalog.py`) — единый источник: id решений, варианты
  веток, условия, источник в Excel, флаг «переопределяемо».
- **Overrides** — тонкий объект, который проносится от конфига до движка и
  консультируется в точках принятия решений; по умолчанию пуст и не меняет
  поведение.
- **GUI** — отдельная страница: строит дерево из каталога, подсвечивает
  `result.branch_path`, позволяет выбрать ветки и пересчитать.

---

## 5. Этапы

### Этап 0. Подготовка и baseline

**Цель:** убедиться, что проект запускается и тесты зелёные до изменений.

**Задачи:**
1. Прочитать `AGENTS.md`, `minlith_modern/WORKFLOW.md`,
   `docs/planning/BRANCH_GRAPH_SELECTION.md`.
2. Запустить из `minlith_modern/`:
   ```bash
   python -m pytest -q
   python -m ruff check src/ tests/
   ```
3. Зафиксировать фактическое число тестов (на момент написания ТЗ —
   **1219 passed, 5 skipped**) и вывод ruff (**All checks passed**).

**Приёмка:** в отчёте указаны реальные числа прогона; расхождение с ТЗ
зафиксировано.

**Файлы:** не меняются.

---

### Этап 1. Каталог решений `branch_catalog.py`

**Цель:** формализовать вершины/ветки для визуализации и валидации overrides.

**Файлы:**
- Новый: `src/core/excel_parity/branch_catalog.py` (чистый, без Qt).
- Новый тест: `tests/test_branch_catalog.py`.
- Документация: дополнить `docs/planning/BRANCH_GRAPH_SELECTION.md`.

**Задачи:**
1. Добавить дата-классы (имена можно менять, но публичный API пусть будет такой):
   ```python
   @dataclass(frozen=True)
   class BranchInfo:
       id: str            # "H5", "3", "A", "t_67", "C-srp" ...
       title: str         # человекочитаемая подпись
       condition: str = ""
       source: str = ""   # Excel-ячейка/флаг/VBA-процедура

   @dataclass(frozen=True)
   class DecisionSpec:
       id: str            # "coefficient_band", "rock_type", "stage_vi", "type1.d49" ...
       title: str
       stage: str         # "stage0" | "type" | "stage_vi"
       overridable: bool
       branches: tuple[BranchInfo, ...]
   ```
2. Собрать `DECISIONS: dict[str, DecisionSpec]` минимум для:
   - `coefficient_band` → 6 веток (H5/J5/L5/H12/J12/L12) — условия и флаги
     взять из `COEFFICIENT_BAND_INFO` в `branches.py`;
   - `rock_type` → 5 веток (1..5) — из `ROCK_TYPE_INFO`;
   - `stage_vi` → 5 веток (A/B/C-srp/C-mst/C-mst2) — из `STAGE_VI_INFO`.
   - (опционально, для этапа 6) внутренние решения типов — можно завести
     заготовки с `overridable=False` на этом этапе.
3. Добавить функции:
   - `branch_ids(decision_id: str) -> tuple[str, ...]`
   - `find_decision(decision_id: str) -> DecisionSpec`
   - `catalog_to_dict() -> dict` (для GUI/экспорта JSON).
4. Тесты (`tests/test_branch_catalog.py`):
   - все `id` решений уникальны; все `id` веток внутри решения уникальны;
   - у каждого решения ≥ 2 ветки;
   - для трёх MUST-решений id веток совпадают с ключами соответствующих
     `*_INFO` в `branches.py` (защита от рассинхрона);
   - `catalog_to_dict()` сериализуется в JSON (`json.dumps`).

**Приёмка:**
- `python -m pytest tests/test_branch_catalog.py -q` — зелёный.
- Полный `pytest` — без регрессий; ruff чисто.
- В отчёте: перечень решений/веток и число тестов.

**Не делать:** не менять `branches.py` (можно импортировать оттуда
`*_INFO`).

---

### Этап 2. Модель overrides и проброс (без изменения поведения)

**Цель:** пронести выбор пользователя от конфига до движка, ничего не меняя по
умолчанию.

**Файлы:**
- Новый: `src/core/branch_overrides.py`.
- `src/core/models.py` — поля конфига.
- `src/utils/config.py` — дефолты и валидация.
- `src/core/algorithm.py` — поле в `AlgorithmInput`.
- `src/core/calculator.py` — сборка overrides в `_build_algorithm_input`.
- `src/core/excel_parity/algorithm.py` — прокинуть в runner.
- `src/core/excel_parity/runner.py` — принять `overrides`.
- `src/core/excel_parity/stage0.py` — поле `Stage0.overrides` (по умолчанию
  `None`).
- Тест: `tests/test_branch_overrides.py`.

**Задачи:**
1. `src/core/branch_overrides.py`:
   ```python
   @dataclass(frozen=True)
   class BranchOverrides:
       choices: dict[str, str] = field(default_factory=dict)   # decision_id -> branch_id
       forced_path: tuple[str, ...] = ()                       # (этап 6) ordered branch ids
       def get(self, decision_id: str) -> str | None: ...
       def is_empty(self) -> bool: ...
       def to_dict(self) -> dict: ...
   ```
   Плюс функция валидации `validate_overrides(ov) -> None` (использует
   `branch_catalog`; недопустимая ветка → `ValueError` со списком допустимых).
2. `CalculationConfig` (`models.py`): добавить
   `branch_overrides: dict[str, str] = field(default_factory=dict)` и
   `forced_path: tuple[str, ...] = ()` (с дефолтами, обратно совместимо).
3. `DEFAULT_CONFIG` (`config.py`): `"branch_overrides": {}`,
   `"forced_path": []`; в `validate()` — тип/допустимость (если задано).
4. `AlgorithmInput` (`algorithm.py`): добавить
   `overrides: BranchOverrides | None = None`.
5. `Calculator._build_algorithm_input` (`calculator.py`): собрать `BranchOverrides`
   из `self.config` и положить в `AlgorithmInput.overrides`. Если пусто — `None`.
6. `ExcelParityAlgorithm.compute` / `runner.run_from_stage0` /
   `runner.run_sample` / `compute_stage0`: принять `overrides` и положить в
   `Stage0.overrides`. Пока **нигде не использовать** — поведение не меняется.
7. Тесты: пустые overrides дают тот же результат, что и без них (сравнить
   `run_sample(...)` и `run_sample(..., overrides=пусто)`); невалидный выбор →
   `ValueError`.

**Приёмка:**
- Все прежние тесты зелёные (дефолт не изменился).
- Новые тесты зелёные; ruff чисто.

---

### Этап 3. Overrides в движке: `rock_type`, `coefficient_band`, `stage_vi`

**Цель:** реально применять выбранные ветки.

**Файлы:**
- `src/core/excel_parity/stage0.py`
- `src/core/excel_parity/stage_vi.py`
- `src/core/excel_parity/runner.py` (`ExcelRun.path` — помечать принудительные)
- `src/core/branches...` (без изменений)
- `src/core/excel_parity/branches.py` — при необходимости добавить поле
  `forced` в маршрут (сделать **аддитивно**, с дефолтом).
- Тест: `tests/test_branch_overrides.py` (дополнить).

**Задачи:**
1. `coefficients(f, a, override=None)`: если `override` есть и валиден (из
   `branch_ids("coefficient_band")`) — вернуть коэффициенты **этой** полосы
   (формулы уже есть в функции; вынести выбор полосы так, чтобы он уважал
   override). `coefficient_band(f, a)` остаётся авто-функцией.
2. `classify(fe, k1, k3, override=None)`: если `override` задан — вернуть
   `int(override)` (предварительно валидировать 1..5).
3. `compute_stage0(ox, overrides=None)`: прокинуть override в `coefficients` и
   `classify`; помнить про `stage_vi`.
4. `solve_stage_vi(st0, tsol, override=None)`: если override из
   `branch_ids("stage_vi")` — выполнить формулы этой ветки (A/B/C-srp/C-mst/
   C-mst2) вместо авто-выбора. **Внимание:** ветки сейчас — это `if/elif`;
   реализуйте выбор ветки параметром, сохранив существующие формулы
   дословно (паритет!). Если выбор ветки несовместим с текущими остатками —
   всё равно применяйте формулы (это эксперимент пользователя), но
   задокументируйте это.
5. `ExcelRun.path`: у принудительных решений выставлять признак
   (`BranchDecision.forced = True` или в `to_dict` поле `"forced": true`).
   Сделать так, чтобы существующий `to_dict()` **не ломался** (ключи
   добавляются, старые остаются).
6. `CalculationResult.branch_path` уже прокидывается — ничего не менять.

**Тесты (`tests/test_branch_overrides.py`):**
- Для каждого `rock_type` 1..5: принудительный выбор → в `path` есть
  `rock_type_N`, `force=True`; результат (минералы) детерминирован.
- Для каждой полосы: принудительный выбор → `path` содержит `band_*`, значения
  k1..k4/achl равны формулам этой полосы (`pytest.approx`).
- Для `stage_vi` A/B/C-*: принудительный выбор → в `path` есть эта ветка.
- **Инвариант:** без overrides результат в точности равен `run_sample` без
  overrides (или `excel_port(rounding=False)` для референсных образцов).

**Приёмка:** все тесты зелёные; дефолтный паритет не нарушен (проверяется
существующими `tests/test_excel_parity.py`).

---

### Этап 4. GUI: страница «Граф разветвлений»

**Цель:** пользователь видит граф решений, маршрут образца и может выбрать
ветки и пересчитать.

**Файлы:**
- Новый: `src/gui/pages/branch_graph_page.py` (`BranchGraphPage(QWidget)`).
- `src/gui/main_window.py` — интеграция (навигация, данные).
- Возможные вспомогательные: `src/gui/widgets/` (если понадобится
  переиспользуемый виджет дерева).
- Тест: `tests/test_branch_graph_page.py` (offscreen) и/или unit-тесты чистых
  хелперов.
- Документация: `README.md`, `WORKFLOW.md`, `docs/reference/API_REFERENCE.md`.

**Требования к странице:**
1. **Выбор образца**: селектор (можно переиспользовать идею
   `SampleSelectorDialog` из `charts_page.py`; либо `QComboBox` со списком
   результатов).
2. **Дерево решений** (`QTreeWidget`): строится из `branch_catalog.DECISIONS`,
   сгруппировано по стадиям («Стадия 0 → Полоса», «Стадия 0 → Тип», «Тип
   породы → ветки», «Этап VI»).
3. **Подсветка маршрута**: узлы/ветки, встречающиеся в
   `result.branch_path["labels"]`, выделяются (жирным/цветом). Принудительные —
   другим цветом.
4. **Выбор ветки**: для решений с `overridable=True` — контрол выбора
   (например, `QComboBox` веток или кнопка «Принудительно» рядом с веткой).
5. **Пересчёт**: кнопка «Пересчитать с выбранными ветками» → собрать
   `CalculationConfig` (по образцу
   `src/gui/dialogs/calculation_dialog.py::_configure_calculator`) с
   `branch_overrides`, прогнать `Calculator.calculate_single(sample)`, обновить
   дерево/маршрут и показать сводку результата (минералы/тип).
6. **Сброс**: кнопка «Снять все принудительные ветки» → пересчёт «как есть».

**Интеграция в `main_window.py` (аккуратно с индексами!):**
- добавить `("Граф", "<иконка>")` в `_page_names`;
- создать `self._branch_graph_page = BranchGraphPage(self._config)`;
- добавить в `self._stack` **в том же порядке**;
- обновить горячие клавиши-индексы и сигнал `_on_calculation_done` /
  `calculate_batch`, чтобы страница получала результаты
  (`set_results(results)`).
- Проверить, что индексы `_switch_page`, `Ctrl+D`/`Ctrl+R` не съехали.

**Тесты:**
- Pure-функции (построение строк дерева из каталога+маршрута) покрыть
  юнит-тестами **без Qt**.
- Offscreen smoke (если в проекте есть инфраструктура): создать `QApplication`
  с `QT_QPA_PLATFORM=offscreen`, инстанцировать страницу, вызвать
  `set_results([])` и `set_results([result])`, убедиться что не падает.

**Приёмка (ручная проверка ревьюером):**
- страница открывается из сайдбара;
- дерево строится; маршрут подсвечен;
- принудительный выбор меняет маршрут и результат, принудительные ветки видно;
- «Снять все» возвращает авто-результат.

---

### Этап 5. Экспорт и сравнение маршрутов (SHOULD)

**Файлы:**
- `src/core/branch_report.py` (дополнить чистыми функциями).
- `src/gui/pages/branch_graph_page.py` (кнопки экспорта/сравнения).
- `tests/test_branch_report.py` (новый или дополнить `test_branch_path.py`).

**Задачи:**
1. Чистые функции:
   - `branch_path_json(path) -> str` (сериализация маршрута),
   - `diff_branch_paths(path_a, path_b) -> list[...]` (различия: решения,
     где ветки отличаются).
2. Кнопка «Экспорт маршрута (JSON)» и «Экспорт дерева (PNG/SVG)» (если
   реализуете PNG/SVG — только через matplotlib, как в `src/charts/`).
3. Кнопка «Сравнить с авто»: показать таблицу различий авто vs принудительный
   маршрут.

**Приёмка:** функции покрыты тестами; на странице доступен экспорт и сравнение.

---

### Этап 6. Override внутренних веток типов (SHOULD, самый большой)

**Цель:** разрешить выбирать ветки внутри типов 1–5 (например, `t_67`,
`F119+`, `m_322t->p81`).

**Файлы:**
- `src/core/excel_parity/branch_catalog.py` (добавить решения типов).
- `src/core/excel_parity/types.py` (инструментировать решения).
- `tests/test_branch_overrides_internal.py`.

**Подход (важно!):** код типов — императивное дерево `if/else`. Для каждого
решения:
1. Заведите в каталоге `DecisionSpec` с `id` вида `"type3.p_114"`,
   `overridable=True`, и перечислите ветки (id = подписи, которые сейчас
   попадают в `TypeSolution.trace`).
2. В `types.py` в точке выбора:
   ```python
   forced = overrides.get("type3.p_114") if overrides else None
   chosen = forced if forced in {<допустимые ветки>} else auto_choice
   ```
   где `auto_choice` — прежняя логика. Формулы веток не менять.
3. `trace` должен отражать принудительную ветку (как обычно) и признак
   `forced`.

**Ограничение объёма:** реализуйте по возможности **все** решения, перечисленные
в `TYPE_BRANCH_INFO` (`src/core/excel_parity/branches.py`), но помечайте
выполненные в отчёте. Если решение невозможно переопределить без искажения
паритета — оставьте `overridable=False` и объясните.

**Тесты:** для каждого переопределяемого решения — принудительный выбор
приводит к появлению соответствующей подписи в `path` и к изменению результата
относительно авто (где ветки реально различаются). Инвариант «без overrides —
как раньше» обязателен.

**Приёмка:** список переопределяемых решений зафиксирован в отчёте и в
`branch_catalog.py`; тесты зелёные; дефолт неизменен.

---

### Этап 7. Финализация

**Задачи:**
1. Обновить документацию (в том же этапе, что и код):
   - `minlith_modern/CHANGELOG.md` — раздел `[Unreleased]`;
   - `minlith_modern/README.md` — возможности/GUI, **счётчик тестов** (два
     места: «# Все тесты (N)» и «tests/ # N тестов»);
   - `minlith_modern/WORKFLOW.md` — структура, паттерны, **счётчик тестов**;
   - `docs/reference/API_REFERENCE.md` — новые публичные API
     (`branch_catalog`, `branch_overrides`, поля конфига);
   - `docs/planning/todo2.md` — строка статуса;
   - `docs/planning/BRANCH_GRAPH_SELECTION.md` — отметить реализованное;
   - `docs/README.md` — если добавлялись новые md-файлы.
2. Прогнать финально `pytest` и `ruff`, зафиксировать числа.
3. Ручная проверка GUI (см. этап 4 «Приёмка»).

---

## 6. Сквозные требования

- **Паритет:** после каждого этапа `tests/test_excel_parity.py` и
  `tests/test_excel_parity_property.py` должны быть зелёными. Если сомневаетесь
  в изменении формул — сверяйтесь с `excel_port` (оракул).
- **Обратная совместимость:** все новые поля дата-классов — с дефолтами;
  старые вызовы не должны требовать правок.
- **Тесты:** каждая новая публичная функция — минимум один тест. Чистая
  логика — без Qt; GUI — offscreen.
- **Docs:** см. этап 7. Числа — из фактического прогона.
- **Не трогать:** позиционные реестры диаграмм (23), движки `excel_exact`/
  `geological_theory`, существующий паритет.

---

## 7. Definition of Done

- [ ] `branch_catalog.py` + тесты.
- [ ] `branch_overrides.py` + проброс config→движок (дефолт не изменён).
- [ ] Overrides работают для `rock_type`, `coefficient_band`, `stage_vi`.
- [ ] GUI-страница «Граф»: дерево, подсветка маршрута, выбор ветки, пересчёт, сброс.
- [ ] Экспорт маршрута и сравнение авто/принудительного маршрута (SHOULD).
- [ ] Переопределение внутренних веток типов (SHOULD) — со списком реализованных.
- [ ] Паритет-тесты зелёные; дефолтное поведение не изменилось.
- [ ] `python -m pytest -q` и `python -m ruff check src/ tests/` — зелёные/чисто.
- [ ] Документация обновлена, счётчики совпадают с реальным прогоном.
- [ ] Отчёт по этапам с числами и списком файлов.

---

## 8. Риски и подводные камни

1. **Паритет легко сломать.** Любая правка формул в `types.py`/`stage0.py`/
   `stage_vi.py` рискует изменить дефолтный результат. Override должен быть
   **строго аддитивным** (пустой override == прежнее поведение).
2. **Именованные ячейки Excel.** В движке есть места, где значение зависит от
   «залипших» именованных ячеек (`mg0` и т.п.). Не путайте override с этими
   квирками; override — это новое поведение, а не исправление паритета.
3. **Индексы страниц в `main_window.py`.** Добавление страницы сдвигает
   индексы — обновите все ссылки (навигация, `Ctrl+*`, `_switch_page`).
4. **Позиционные реестры диаграмм.** Не добавляйте через них граф; используйте
   отдельную страницу.
5. **`stage_vi` override.** Ветки частично вложены; при несовместимых остатках
   формулы могут дать «шумные» значения — это допустимо для эксперимента, но
   должно быть явно помечено в UI.
6. **Qt-offscreen.** GUI-тесты запускайте с `QT_QPA_PLATFORM=offscreen`;
   чистую логику выносите в отдельные функции без Qt.

---

## 9. Приложение

### 9.1. Команды

```bash
# из minlith_modern/
python -m pytest -q
python -m ruff check src/ tests/
python -m pytest tests/test_excel_parity.py -q      # инвариант паритета
python -m pytest tests/test_branch_catalog.py -q
python -m pytest tests/test_branch_overrides.py -q

# ручной запуск GUI (Windows)
python -m src.main         # или run.bat
```

### 9.2. Мини-пример overrides (как это должно выглядеть в коде)

```python
from src.core.models import CalculationConfig, OxideComposition, Sample
from src.core.calculator import Calculator

comp = OxideComposition(sio2=70.0, al2o3=12.0, fe2o3=1.0, feo=0.5,
                        mgo=0.3, cao=0.5, na2o=3.0, k2o=6.0)
sample = Sample(name="X", composition=comp)

cfg = CalculationConfig(
    calculation_engine="excel_parity",
    branch_overrides={"rock_type": "3", "coefficient_band": "H12"},
)
result = Calculator(config=cfg).calculate_single(sample)
print(result.rock_type)          # принудительно 3
print(result.branch_path)        # содержит forced-ветки
```

### 9.3. Идентификаторы решений (MUST-уровень)

| decision_id | Ветки (branch_id) | Источник |
|---|---|---|
| `coefficient_band` | `H5`, `J5`, `L5`, `H12`, `J12`, `L12` | `COEFFICIENT_BAND_INFO` |
| `rock_type` | `1`, `2`, `3`, `4`, `5` | `ROCK_TYPE_INFO` |
| `stage_vi` | `A`, `B`, `C-srp`, `C-mst`, `C-mst2` | `STAGE_VI_INFO` |

Внутренние решения типов (этап 6) — id задаются в `branch_catalog.py`;
ветки = подписи из `TYPE_BRANCH_INFO` (`t_*`, `p_*`, `m_*`, `D*`, `F*`, `s_*`).

### 9.4. Карта файлов (что где менять)

| Слой | Файлы |
|---|---|
| Каталог | `src/core/excel_parity/branch_catalog.py` (new), `branches.py` |
| Overrides | `src/core/branch_overrides.py` (new), `models.py`, `utils/config.py`, `core/algorithm.py`, `core/calculator.py` |
| Движок | `src/core/excel_parity/{stage0,stage_vi,types,runner,algorithm}.py` |
| GUI | `src/gui/pages/branch_graph_page.py` (new), `src/gui/main_window.py`, при необходимости `src/gui/dialogs/`, `src/gui/widgets/` |
| Чистая логика | `src/core/branch_report.py` |
| Тесты | `tests/test_branch_catalog.py`, `tests/test_branch_overrides.py`, `tests/test_branch_overrides_internal.py`, `tests/test_branch_graph_page.py` |
| Docs | `CHANGELOG.md`, `README.md`, `WORKFLOW.md`, `docs/reference/API_REFERENCE.md`, `docs/planning/todo2.md`, `docs/planning/BRANCH_GRAPH_SELECTION.md`, `docs/README.md` |

### 9.5. Формат отчёта исполнителя (по каждому этапу)

```
Этап N — <название>
Сделано: <кратко>
Файлы: <список>
Тесты: pytest => X passed, Y skipped; ruff => All checks passed
Проверка: <как проверяли, что работает>
Проблемы/расхождения с ТЗ: <если есть>
Следующий шаг: <этап N+1>
```
