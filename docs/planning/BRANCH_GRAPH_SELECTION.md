# Система графов для выбора пользователем разветвления — контекст

**Статус:** черновик-контекст (материал для размышления, НЕ ТЗ и НЕ план).
Часть базы уже реализована: структурированная траектория веток
`excel_parity` (`src/core/excel_parity/branches.py`, `ExcelRun.path`,
`AlgorithmOutput.path`) и подсчёт сходимости обоих Excel-движков в
`scripts/verify_excel_parity.py`.
**Дата:** 2026-09-21
**Назначение:** собрать в одном месте всё, что нужно знать о проекте, чтобы
спроектировать функционал «пользователь выбирает разветвление алгоритма»
(далее — «граф разветвлений» / «выбор ветки»).

> **ТЗ на реализацию:** `TZ_BRANCH_GRAPH.md` (в этой же папке) — этапы,
> критерии приёмки, идентификаторы решений.
>
> **Прогресс:** ✅ этап 1 — каталог решений (`src/core/excel_parity/branch_catalog.py`);
> ✅ этап 2 — модель override и проброс (`src/core/branch_overrides.py`,
> `CalculationConfig.branch_overrides`, `AlgorithmInput.overrides`, `Stage0.overrides`);
> ✅ этап 3 — применение override в движке (`coefficients`/`classify`/`solve_stage_vi`,
> пометка `forced` в `ExcelRun.path`);
> ✅ этап 4 — GUI-страница «Граф» (`src/gui/pages/branch_graph_page.py`, дерево + маршрут +
> выбор ветки + пересчёт; сайдбар «Граф»);
> ✅ этап 5 — экспорт маршрута (JSON) и сравнение «авто vs принудительно»
> (`branch_report.branch_path_json/diff_branch_paths`, кнопки на странице «Граф»).
> 🟡 этап 6 (частично) — override внутренних решений: `type3.p_114` (F119+/F126-),
> `type45.d418` (m_418t/m_424->t5), `type1.t_49` (t_52~53/t_58/t_67/t_83),
> `type3.d61` (D61/D68), `type3.d200` (3333a/3333b), `type3.p_142` (p_142/no_p_142),
> `type2.fe_ill`, `type3.d180`, `type2.an`, `type2.s204`, `type2.ill_or`,
> `type3.d162`, `type3.d188`, `type3.p_53`, `type3.p_97`, `type45.d334`, `type45.d346`,
> `type1.t_73`, `type45.d287/d302/d322/d294/d308/d317` (всего **24** решения —
> покрыты все бинарные развилки типов 1/2/3/4-5; остаются только заглушки
> `overridable=False` для сгруппированных подписей). `overrides` для хелперов
> type4/5 проносится через поле `TypeSolution.overrides`.
> (`branch_catalog._TYPE_STUBS`) и требуют поштучной инструментовки.

> Этот файл отвечает на вопрос «что у нас есть и как оно устроено», чтобы
> потом принять продуктовые/архитектурные решения. Решения и открытые вопросы —
> в разделах 9–12.

---

## 0. Постановка задачи

Алгоритм MINLITH — это по сути **большое дерево решений**: на каждом шаге
вычисляется условие, и расчёт идёт по одной из веток. Сейчас движок выбирает
ветку **автоматически**. Гипотетический функционал — дать пользователю:

- **видеть** граф разветвлений (дерево решений) и маршрут конкретного образца;
- **выбирать** ветку вручную (override) и пересчитывать;
- **сравнивать** результаты разных маршрутов.

Ключевой вопрос продукта: выбор ветки — это **диагностика** (посмотреть, куда
пошёл алгоритм), **эксперимент** (а что если?), или **влияние на результат**
(пользователь настаивает на своей ветке)? От ответа зависит вся архитектура.

---

## 1. Что такое «разветвление» в MINLITH

Ветвления образуют три вложенных уровня:

1. **Тип породы 1–5** — глобальная классификация по балансу Al/Na/K/Mg и
   коэффициентам k1/k3.
2. **Полоса F/A → коэффициенты k1..k4 и achl** — выбор одной из 6 «полос»
   (таблица кандидатов в Excel), задающей стехиометрию хлорита.
3. **Внутренние ветви типа** — дерево распределения Al/Si (плагиоклаз, иллит,
   хлорит, каолинит/гиббсит, монтмориллонит, остатки), а затем **стадия VI**
   (распределение Ca/Mg/Fe/Mn по карбонатам/оксидам).

Носители ветвления в оригинале:

- **VBA-макросы** (`Ispravlenny_MINLITH1_2010.xlsm`) — это «поток управления»:
  конструкции `If Range(...)`, которые копируют значения ячеек в именованные
  диапазоны. По дампу `vba_structure.json` — **~117 точек `If Range`**.
- **Формулы листов** «Нач+Type 12» (типы 1–2) и «Нач+Type 3» (типы 3–5):
  вычисляют флаги-условия (например `F20..F26`, `G17..I18`, `D49`, `D177`…).

В Python ветвление воспроизведено кодом (см. раздел 2).

---

## 2. Где сейчас «живут» ветвления — карта кода

### 2.1. Выбор движка (мета-уровень)

| Что | Файл:строка |
|---|---|
| Протокол алгоритма `MineralAlgorithm.compute` | `minlith_modern/src/core/algorithm.py:109` |
| Диспетчер движка `Calculator._algorithm_for_engine` | `minlith_modern/src/core/calculator.py:89-117` |
| Канонические имена движков `CALCULATION_ENGINES` | `minlith_modern/src/core/models.py:176` |
| Алиасы legacy `LEGACY_ENGINE_ALIASES` | `minlith_modern/src/core/models.py:181` |
| Дефолт в конфиге | `minlith_modern/src/utils/config.py:27` |
| Валидация значения | `minlith_modern/src/utils/config.py:189` |
| CLI `--engine` | `minlith_modern/src/cli.py:460` |

Текущие движки: `excel_parity` (алгоритм Excel без пошаговых ROUND, дефолт),
`excel_exact` (полная 1:1 копия Excel с ROUND), `geological_theory`
(самостоятельная теория), `python_rework` (плейсхолдер → теория).

### 2.2. Классификация типа породы — **4 независимых реализации**

| # | Классификатор | Файл:строка | Логика |
|---|---|---|---|
| 1 | `Calculator._classify_type` (legacy) | `src/core/calculator.py:217-233` | пороги по ф.е.: `al ≤ 1.2na+k →1`, `≤1.2na+3.25k →2`, `k1≈0 →5`, t3, t4 |
| 2 | `excel_parity.stage0.classify` | `src/core/excel_parity/stage0.py:158-184` | «дефекты» `e20..e25`; `e20<0 or e21≤0→1`, `e22≤0→2`, `e24≤0→3`, `e25≤0→4`, иначе 5 |
| 3 | `excel_port.stage0.classify` | `src/core/excel_port/stage0.py:121-134` | читает флаги листа `F20..F26` |
| 4 | `stage2.classify_rock_type` (теория) | `src/core/stage2.py:30-48` | по `R = Al/(Na+K+Ca)`, пороги `[1.0, 1.5, 2.5, 5.0]` |

> Расхождения классификаторов — исторические и намеренные (разные алгоритмы),
> но для «графа выбора» это важно: у одного и того же образца может быть
> разный тип в зависимости от движка.

### 2.3. Выбор коэффициентов k1..k4/achl по F/A

| # | Реализация | Файл:строка | Логика |
|---|---|---|---|
| 1 | `excel_parity.stage0.coefficients` | `src/core/excel_parity/stage0.py:114-155` | каскад 6 полос F (и A для F 0.69–0.87) |
| 2 | `excel_port.stage0.select_coefficients` | `src/core/excel_port/stage0.py:82-105` | по флагам `G17,H17,I17,J17,G18,I18` читает колонки `H/J/L` строк 5..9 или 12..16 |
| 3 | `coefficients.calculate_coefficients` (legacy) | `src/core/coefficients.py:10-67` | 5 F-полос; **игнорирует A** |

Сам каскад (порядок как VBA `u_0..u_10`): F∈(0,0.21)→H5:H9, [0.21,0.51)→J5:J9,
[0.51,0.69)→L5:L9, [0.69,0.87)+A>0.47→H12:H16, [0.69,0.87)+0.40<A<0.47→J12:J16,
иначе→L12:L16. Формулы ячеек — `excel_port/data/workbook_raw.json` (H5..L16),
флаги — строки `G17..I18`.

### 2.4. Внутренние ветви типов (ядро дерева)

| Что | Файл | Объём |
|---|---|---|
| Точный порт VBA-ветвлений типов 1–5 | `src/core/excel_parity/types.py` | 1125 строк; десятки веток `t_*`, `p_*`, `s_*`, `m_*` |
| Стадия VI (Ca/Mg/Fe/Mn) | `src/core/excel_parity/stage_vi.py:32-90` | ветки A/B/C + защитный `NotImplementedError` |
| Legacy-формулы типов 1–5 | `src/core/types_logic.py` | `calculate_type1..5` + `stage_vi` |
| Диспетчер подстадии типов (parity) | `src/core/excel_parity/types.py:57-66` | `t==1→type1`, `t==2→type2`, `t==3→type3`, иначе `type45` |

Примеры «развилок» внутри типов (для понимания масштаба):

- `types.py:423` и `types.py:456` — **явные gap-и** (`NotImplementedError`)
  для редких веток Fe-пути типа 3.
- `stage_vi.py:90` — защитная ветка «ни A, ни B, ни C не сошлись».
- Ветка типа 5: `aType_5 → m_274 | m_528` и далее `m_538, m_540, m_542, m_549,
  m_551, m_552`.

### 2.5. Полный кадастр VBA-веток

Дамп `minlith_modern/src/core/excel_port/data/vba_structure.json` содержит все
`If Range` по процедурам (`aDefin`, `ca_1`, `u0`, `v_1`, `aType_5`, `aType_4`,
`p_*`, `s_*`, `t_*`, `rVI`, `aut_2`…). Это **машинночитаемый источник истины**
для автоматической генерации графа (см. раздел 12).

---

## 3. Что уже есть для «траектории решения»

| Механизм | Файл:строка | Что даёт | Чего не хватает |
|---|---|---|---|
| `BranchPath` / `BranchDecision` (реализовано) | `src/core/excel_parity/branches.py` | структурированный маршрут: полоса коэффициентов, тип, подписи веток типа и VI этапа + каталоги условий | нет записи всех ~60 внутренних микро-веток с условиями (условия дозаполняются); нет визуала |
| `ExcelRun.path` / `AlgorithmOutput.path` (реализовано) | `src/core/excel_parity/runner.py`, `src/core/algorithm.py` | маршрут образца наружу из движка | в `ChartData` ещё не прокинут |
| `DebugTraceCollector.record_branch_path()` (реализовано) | `src/core/debug_tracer.py` | маршрут попадает в `conditions` при `debug=True` | — |
| `DebugTraceCollector` / `TraceStep` / `TraceCondition` | `src/core/debug_tracer.py:11-77` | модель «условие → результат → ветка», `to_dict/to_text/export_json` | **не заполняется условиями** в расчёте (кроме нового `record_branch_path`); в `ChartData` не попадает |
| `excel_parity` текстовые подписи веток | `types.py` (`tsol.trace`), `stage_vi.py` (`vi.trace`) | строки вида `t_52`, `p_253` | нет структуры (только текст), не привязано к условиям/ячейкам |
| VM-журнал выполнения VBA | `src/core/excel_port/vm.py` (`call_log`, `assignments`) | фактический маршрут по VBA-процедурам | сырой, не нормализован под «граф» |
| `DebugTrace` в результате | `src/core/models.py:221` (`CalculationResult.debug_trace`) | доступен из `calculate_single(debug=True)` | GUI/диаграммы его не читают |

**Вывод:** «скелет» трассировки условий уже есть, но траектория автоматически
**не строится** и в визуальный слой **не выведена**. Это главный разрыв.

---

## 4. Как устроен «выбор пользователем» сейчас (шаблон)

Выбор движка — готовый пример «пользователь выбирает вариант расчёта»:

1. Ключ в конфиге: `ConfigManager` → `minlith_modern/src/utils/config.py:27`.
2. Набор допустимых значений: `models.CALCULATION_ENGINES:176`.
3. Фабрика: `Calculator._algorithm_for_engine:89`.
4. CLI: `src/cli.py:460`.
5. GUI-тулбар: `src/gui/main_window.py:59-103` + `_set_engine:392` +
   `_update_engine_buttons:401`.
6. GUI-настройки: `src/gui/pages/settings_page.py:349-369`, сохранение `:615`.
7. Диалог расчёта с per-run override: `src/gui/dialogs/calculation_dialog.py:23-28,
   64-73, 132-151`.

Паттерн «настройка → фабрика/движок → пересчёт → сброс устаревших результатов»
(`main_window._on_settings_changed:352`) можно переиспользовать для выбора ветки.

---

## 5. Инфраструктура визуализации (куда «вешать» граф)

### 5.1. Диаграммы

- 23 matplotlib-плагина (`src/charts/built_in/`) + 14 интерактивных Plotly
  (`src/charts/engines/plotly_charts.py`).
- Единая сборка данных: `build_chart_data()` — `src/charts/data_builder.py:46`.
- Контейнер данных `ChartData` — `src/charts/base.py:13-31`:
  `sample_names, oxides, minerals_wt, minerals_fu, defect, rock_types,
  F_values, A_values, metadata` (свободный `metadata` — удобная точка для
  траектории/узлов).
- **Регистрация позиционная и хрупкая:** `BUILTIN_CHARTS`
  (`src/charts/built_in/__init__.py:27`), `BUILTIN_TYPE_IDS` +
  `SPECS` (`src/gui/widgets/chart_interactions.py:77,127`),
  `BUILTIN_SIZE_IDS` + `STANDARDS` (`src/gui/widgets/chart_sizes.py:54,83`).
  `_validate_registry`/`_validate_standards` требуют **ровно 23**, иначе импорт
  падает.
- Ближайшие «родственники» графа: фазовые поля **TAS/QAPF/Feldspar/ACNK/AFM/
  SiO₂-K₂O** (статичные полигоны/линии — образец рисования областей) и
  **Dendrogram** (единственное «дерево», но это кластеризация образцов, не
  дерево решений).
- **Plotly TreeMap/Sankey/Icicle сейчас не используются** — естественные
  кандидаты для интерактивного графа.

### 5.2. GUI

- Сетка плиток `MultiChartView` — `src/gui/widgets/chart_grid.py:827`;
  клики/наведение уже поддержаны (`_on_click:322`, `_on_hover:303`, образец —
  pie-explode).
- Готовый селектор «выбрать что угодно чекбоксами + Все/Снять/Инверсия»:
  `SampleSelectorDialog` — `src/gui/pages/charts_page.py:31`.
- Правила интерактива: `docs/CHART_INTERACTIONS_SPEC.md` (§7 — «сначала строка
  в реестре, потом рендерер»; §13 — запрет ветвлений по типу вне реестра;
  поведение в `InteractionSpec`).
- Чистая математика (раскладка/хит-тест) — `src/gui/widgets/zoom_math.py`
  (без Qt/matplotlib).

### 5.3. Отчёты

Чтобы граф попадал в PDF/Word/HTML/LaTeX, нужны правки в трёх местах:
`CHART_ALIASES` (`src/reports/chart_renderer.py:20`),
`CHART_TYPES` (`src/gui/pages/reports_page.py:55`),
`BlockType.CHART` (`src/reports/template_builder.py:18`).

---

## 6. Поток данных и «разрыв»

```
Sample ──► Calculator.calculate_single
              ├─ Stage0 (классификация типа, коэффициенты)   ← развилки №1-2
              ├─ Algorithm.compute (дерево типов + стадия VI) ← развилки №3
              └─ CalculationResult (.debug_trace, .rock_type, .coefficients)
                        │
                build_chart_data()
                        ▼
                    ChartData(metadata) ──► GUI (MultiChartView/ChartPage) / Отчёты
```

**Разрыв:** движки не возвращают структурированный «маршрут» (список
пройденных условий/веток), а `ChartData` не имеет под это поля — только
произвольный `metadata`. Любой граф потребует сначала **собрать маршрут в
`core`**, затем **прокинуть его в `ChartData`**.

---

## 7. Как добавить новую диаграмму (чеклист проекта)

1. `src/charts/built_in/<name>.py` — класс-наследник `ChartPlugin`.
2. Добавить в `BUILTIN_CHARTS` (`built_in/__init__.py:27`) — **в конец**.
3. `type_id` в `BUILTIN_TYPE_IDS` (`chart_interactions.py:77`) + запись в `SPECS`.
4. `type_id` в `BUILTIN_SIZE_IDS` (`chart_sizes.py:54`) + `STANDARDS`.
5. (опц.) `CHART_ALIASES` и/или `CHART_TYPES` для отчётов.
6. (опц.) интерактив: `fig_<t>`/`interactive_<t>` + 4 структуры Plotly.
7. Тесты: `tests/test_charts.py`, `tests/test_plotly_charts.py`,
   `tests/test_chart_export.py`.
8. Документация по `AGENTS.md` (README/CHANGELOG/WORKFLOW/API_REFERENCE/todo2).

---

## 8. Обязательные ограничения и правила

- **Паритет:** `excel_parity == excel_port(rounding=False)` на решётке
  16000/16000; 3 явных gap (`NotImplementedError`). Любой override не должен
  менять поведение по умолчанию.
- **Реестры диаграмм строго позиционные** и проверяются на «ровно 23».
- **SPEC §13:** поведение при взаимодействии описывается в `InteractionSpec`,
  а не ветвлением по типу в `chart_grid.py`.
- **AGENTS.md:** изменение кода/поведения ⇒ обновление md-файлов; числа в
  документации — из фактического прогона `pytest`.
- **Счётчики:** сейчас `1192 passed, 5 skipped`; диаграмм 23 matplotlib + 14
  Plotly.

---

## 9. Пространство решений (для обдумывания)

### 9.1. Что именно выбирает пользователь

- **A1. Тип породы вручную** (override классификации №1/№2/№3).
- **A2. Полосу коэффициентов** (override `k1..k4/achl`; «как в Excel» — выбор
  колонки H/J/L).
- **A3. Конкретную бинарную развилку внутри типа** (override флага/условия,
  напр. `d180`, `chl по Si/Mg/Fe`).
- **A4. Путь целиком** (последовательность развилок — «сценарий»).

### 9.2. Как передавать выбор в движок

- **B1. Карта override `{branch_id: choice}`** в конфиге/запуске.
- **B2. «Сценарий» значений именованных переменных Excel** (как VBA пропускает
  `If`, подставляя ячейки).
- **B3. Новый движок/режим** («ручной маршрут»), изолированный от паритета.

### 9.3. Как представить визуально

- **C1. Статичное дерево решений** (matplotlib) с подсветкой маршрута образца —
  по аналогии с TAS/QAPF-полями.
- **C2. Интерактивный граф** (Plotly `TreeMap`/`Sankey`/`Icicle`) с кликом по
  узлу для выбора.
- **C3. Панель-чеклист развилок** (паттерн `SampleSelectorDialog`) + кнопка
  «пересчитать с выбранными ветками».

### 9.4. Охват и назначение

- один образец vs все образцы;
- только просмотр/диагностика vs влияние на результат;
- сравнение двух маршрутов (в духе `Bland-Altman`/heatmap).

### 9.5. Единая таксономия веток

Нужен стабильный `branch_id`. Кандидаты на источник:
- Excel-ячейка/флаг (`G17`, `F20`, `D177`, `D49`) — «как в книге»;
- Python-функция/метка (`types.py` подписи `t_52`, `p_253`, `m_274`);
- автоидентификатор из `vba_structure.json` (модуль+процедура+ номер `If`).

Рекомендуется: **ID = (процедура/стадия, исходная ячейка/флаг, Python-метка)**,
чтобы связать визуал, движок и Excel-документацию.

---

## 10. Открытые вопросы (требуют решения пользователя)

1. Выбор ветки **влияет на результат** или это **только визуализация пути**?
2. Нужен ли ручной выбор для всех трёх уровней или только для типа/полосы?
3. Что делать, если выбранная ветка упирается в **gap** (`NotImplementedError`):
   явная ошибка, предупреждение, fallback?
4. Область действия override: один образец, группа, глобально?
5. Хранить ли «сценарии» маршрутов (сохранение/загрузка/экспорт)?
6. Ломать ли паритет при ручном режиме (предлагается — только в явном
   «экспериментальном» режиме, дефолт не трогаем)?
7. Единица визуализации: весь граф алгоритма (сотни узлов) или **подграф**
   текущего типа образца?
8. Нужен ли «граф» как диаграмма (в `BUILTIN_CHARTS`) или как **отдельная
   интерактивная страница** (дерево + выбор + пересчёт)?

---

## 11. Риски

- **Нет декларативного описания дерева** — только код `types.py` (1125 строк)
  и VBA-дамп. Рефакторинг в декларативную структуру — крупный объём.
- **Позиционные реестры диаграмм** — добавление типа = синхронная правка 5
  мест, проверки «ровно 23».
- **Производительность** визуализации на сотнях узлов (особенно matplotlib).
- **Паритет и тесты**: ручной override легко ломает инварианты; нужна строгая
  изоляция (флаг/режим, не влияющий на дефолтный путь).
- **UX**: граф алгоритма сложен для неподготовленного пользователя; нужен
  разумный уровень детализации (подграф по типу, сворачивание).

---

## 12. Возможные шаги (spikes, каждый — самостоятельная проверка)

1. **Инвентаризация дерева.** Извлечь единый список узлов
   (`id, условие, ветки, источник: Excel-ячейка/флаг, Python-функция`) из
   `excel_parity/types.py` и `vba_structure.json` (последний — машинно,
   ~117 `If`). Результат — JSON-каталог веток.
2. **«Снимок маршрута».** Инструментировать `coefficients`, `classify`,
   `solve_type`, `solve_stage_vi`, чтобы возвращать `path: list[branch_id +
   choice]` (в `AlgorithmOutput`/`ExcelRun`).
3. **Прокинуть path в `ChartData.metadata`** и нарисовать статичное дерево с
   подсветкой маршрута (matplotlib, по образцу TAS-полей).
4. **Прототип override.** Конфиг `{branch_id: choice}` → движок использует
   выбранную ветку; сравнить результат с авто-веткой (heatmap/Bland-Altman).
5. **GUI-панель** (паттерн `SampleSelectorDialog`) + пересчёт + индикация
   выбранных/автоматических веток.
6. **Интерактивный граф** (Plotly TreeMap/Sankey) как отдельная страница или
   диаграмма.
7. **Документация и тесты** (каталог веток, покрытие, AGENTS-обновления).

Рекомендуемый порядок: 1 → 2 → 3 (сначала данные и маршрут, потом визуал),
затем решать про 4/5/6.

---

## 13. Карта файлов (быстрый навигатор)

| Область | Ключевые файлы |
|---|---|
| Движки/фабрика | `src/core/calculator.py`, `src/core/models.py`, `src/core/algorithm.py` |
| Порт Excel (без ROUND) | `src/core/excel_parity/{stage0,types,stage_vi,runner,output}.py` |
| Копия Excel (с ROUND) | `src/core/excel_exact/algorithm.py`, `src/core/excel_port/{runner,vm,workbook,stage0}.py` |
| VM/дамп VBA | `src/core/excel_port/vm.py`, `data/vba_structure.json`, `data/workbook_raw.json` |
| Трассировка | `src/core/debug_tracer.py`, `src/core/models.py:221` |
| Диаграммы | `src/charts/base.py`, `src/charts/data_builder.py`, `src/charts/built_in/`, `src/charts/engines/` |
| Реестры диаграмм | `src/gui/widgets/chart_interactions.py`, `src/gui/widgets/chart_sizes.py` |
| GUI | `src/gui/main_window.py`, `src/gui/pages/charts_page.py`, `src/gui/widgets/chart_grid.py`, `src/gui/dialogs/calculation_dialog.py` |
| Отчёты | `src/reports/chart_renderer.py`, `src/gui/pages/reports_page.py`, `src/reports/template_builder.py` |
| Конфиг | `src/utils/config.py` |
| Спец. диаграмм | `docs/CHART_INTERACTIONS_SPEC.md`, `docs/CHART_INTERACTIONS_TODO.md`, `docs/reference/CHARTS_CATALOG.md` |
| Паритет/статусы | `docs/planning/todo2.md`, `minlith_modern/WORKFLOW.md` |

---

## 14. Связанные документы

- `../reference/EXCEL_REFERENCE_MINLITH.md` — формулы оригинала на уровне ячеек.
- `../algorithm/00_overview_and_math_basis.md` — теория (типы, стадии).

---

## 15. Реализация: каталог решений (этап 1, 2026-09-22)

Этап 1 ТЗ `TZ_BRANCH_GRAPH.md` — **статический каталог решений**.

### 15.1. Что добавлено

| Файл | Назначение |
|---|---|
| `src/core/excel_parity/branch_catalog.py` | каталог `DECISIONS` + API (`find_decision`, `branch_ids`, `catalog_to_dict`, `branch_ids`) |
| `tests/test_branch_catalog.py` | 14 тестов на целостность каталога |
| `BRANCH_GRAPH_SELECTION.md` (этот файл) | секции 15.x |

Каталог — **чистый** модуль (без Qt), импортируется только `branches.py`.

### 15.2. Общедоступный API

```python
from src.core.excel_parity.branch_catalog import (
    DECISIONS,               # dict[str, DecisionSpec]
    find_decision,           # find_decision("coefficient_band") -> DecisionSpec
    branch_ids,              # все id веток решения
    catalog_to_dict,         # -> dict (для GUI/экспорта JSON)
)
```

Дата-классы (frozen):

```python
@dataclass(frozen=True)
class BranchInfo:
    id: str          # "H5", "3", "A", "t_67", "C-srp" …
    title: str       # человекочитаемая подпись
    condition: str   # условие выбора
    source: str      # источник: ячейка/флаг/VBA-процедура

@dataclass(frozen=True)
class DecisionSpec:
    id: str                       # "coefficient_band", "rock_type", "stage_vi" …
    title: str
    stage: str                    # "stage0" | "type" | "stage_vi"
    overridable: bool
    branches: tuple[BranchInfo, ...]
```

### 15.3. Состав каталога

**MUST-решения (переопределяемые, `overridable=True`):**

| `id` | stage | Ветки (id) | Источник данных |
|---|---|---|---|
| `coefficient_band` | `stage0` | H5, J5, L5, H12, J12, L12 | `COEFFICIENT_BAND_INFO` (branches.py) |
| `rock_type` | `stage0` | 1, 2, 3, 4, 5 | `ROCK_TYPE_INFO` (branches.py) |
| `stage_vi` | `stage_vi` | A, B, C-srp, C-mst, C-mst2 | `STAGE_VI_INFO` (branches.py) |

**Заготовки внутренних решений типов (этап 6, `overridable=False`, id веток —
сигнатуры из `TYPE_BRANCH_INFO`):**

| `id` | Название | Ветки |
|---|---|---|
| `type12.plagioclase` | Типы 1–2: распределение плагиоклаза | t_52~53, t_58, t_67, t_83, an=0.2na, an=0.2na(I), an=ca, D61, D68 |
| `type12.illite` | Типы 1–2: распределение иллита | ill-kz (D177-D179), ill+or, ill-gb (D274), fe-ill, fe-ill-mg, p_53t, p_142 |
| `type3.chlorite` | Тип 3: распределение хлорита | F119+, F126-, 3331, 3332a, 3332b, 3333a, 3333b, s_271 |
| `type3.exit` | Тип 3: выход в тип 5 | p253->t5, t5 |
| `type45.route` | Типы 4/5: Fe-путь и rVI | t45-aType5, t45-m504, t45-m513->t5, t45-m552t->t5, t45-m418t, t45-m424->t5, type45-normal, D106 |

> Заготовки ниже «реальных» решений этапа 6: они объединяют все ветки из
> `TYPE_BRANCH_INFO` в грубые группы. На этапе 6 группы будут разбиты на
> отдельные решения `overridable=True` (где это безопасно для паритета).

### 15.4. Инварианты (проверяются тестами)

1. Все `id` решений уникальны.
2. Все `id` веток внутри решения уникальны.
3. У каждого решения **≥ 2 ветки** (иначе нет «выбора»).
4. Ветки MUST-решений в точности совпадают с ключами соответствующего
   `*_INFO` в `branches.py` (защита от рассинхрона каталога и движка).
5. `catalog_to_dict()` сериализуется в JSON (без Qt-зависимостей).
- `minlith_modern/docs/EXCEL_VERSION_*.md` — разбор Excel-версии (в т.ч.
  `EXCEL_VERSION_06_rounding.md`, `EXCEL_VERSION_07_vba_flow.md`).
- `minlith_modern/docs/CHART_INTERACTIONS_SPEC.md` — правила интерактива.
- `todo2.md` — статус порта и паритета.
