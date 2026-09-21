# Приближение / отдаление и взаимодействие с диаграммами в GUI

> Обновлено: 2026-09-17 · статус: реализовано (этапы 1–5 по `CHART_INTERACTIONS_SPEC.md`)
> Модули: `chart_grid.py` (UI), `chart_interactions.py` (реестр), `zoom_math.py` (чистая математика)
> Страницы: «Диаграммы» и «Вывод» (`ChartsPage`, `OutputPage`) — обе используют общий виджет `MultiChartView`.
> Документ заменяет прежнюю версию «данные для обсуждения» и описывает итоговое поведение.

---

## 1. Что реализовано

| Возможность | Способ | Где |
|---|---|---|
| Приблизить / отдалить | Кнопки «Приблизить» / «Отдалить» (шаг из настроек, дефолт ×1.2) | `_ChartTile._on_zoom_in/_on_zoom_out`, `chart_grid.py:389-393` |
| Зум колесом к курсору | `scroll_event` канваса; якорь — точка под курсором | `_on_scroll`, `chart_grid.py:723` |
| Модификаторы колеса | Ctrl → зум только X; Ctrl+Shift → зум только Y; Shift → пан X | `modifier_mode`, `_on_scroll` |
| Панорамирование | Наш `pan_x` (в долях диапазона) + отключённый встроенный scroll-зум | `_ChartTile.pan_x`, `chart_grid.py:529` |
| Сброс вида | «По умолчанию» — autoscale или snapshot (равноаспектные/полярные) | `_restore_view`, `reset_view`, `chart_grid.py:676,743` |
| Равноаспектные (TAS, QAPF, AFM…) | Зум единым фактором обеих осей с сохранением аспекта | `_keep_aspect`, `chart_grid.py:314` |
| Полярные (radar) | Зум через `r`-пределы | `zoom_radial` + `_apply_zoom` |
| Круговые (pie) | Hover-подсказка «сектор — %», explode по клику, сброс формы | `_connect_pie_events`, `chart_grid.py:184-274` |
| Синхронизация | Чекбокс «Синхронизировать зум»: группы `sync_group`, пропорционально/абсолютно | `on_tile_view_changed`, `chart_grid.py:892` |
| Шаг зума из настроек | Один параметр на оба вида, применяется к живым плиткам | `set_zoom_step`, `chart_grid.py:378,846` |
| Экспорт текущего вида | Плитка/все плитки → PNG/PDF/SVG; все плитки → один многостраничный PDF без сброса зума | `export_tile`, `export_all`, `export_all_pdf`, `chart_grid.py:1017,1041,1073` |
| Стандарты размеров | Целевой аспект и `max_width` на каждый тип; канвас центрируется, не растягивается | `_apply_display_size`, `chart_sizes.py` |

Ключевые принципы: диаграммы встраиваются как **живые канвасы matplotlib QtAgg**; встроенный scroll-зум matplotlib **отключён**; каждый тип диаграммы получает поведение из **реестра** `InteractionSpec`, без ветвлений по типу в `chart_grid.py`.

---

## 2. Архитектура (три слоя)

```
chart_interactions.py   — реестр InteractionSpec для 23 типов (категория, возможности, sync_group)
chart_sizes.py          — реестр ChartSizeSpec для 23 типов (целевой аспект, max_width, границы)
        │  get_spec(type_id) / get_size_spec(type_id) / resolve_type_id(chart_idx)
        ▼
chart_grid.py           — UI: _ChartTile (канвас + кнопки) и MultiChartView (сетка, синк, экспорт)
        │  zoom_lims / pan_lims / anchor_fraction / value_at_fraction / zoom_radial
        ▼
zoom_math.py            — чистая математика пределов, без Qt и matplotlib
```

Поток данных:

```
чекбоксы → «Построить выбранные»
        ▼
MultiChartView.render()                          chart_grid.py:951
        │  для каждого типа: chart.render(ChartData) → Figure
        ▼
_ChartTile.set_figure(idx, fig, title, chart_type)   chart_grid.py:148
        │  • FigureCanvasQTAgg            — живой канвас
        │  • NavigationToolbar2QT        — урезанная панель
        │  • get_spec(chart_type)        — InteractionSpec
        │  • _apply_spec()               — скрытие/дизейбл неподдерживаемых кнопок и инструментов
        │  • _disable_builtin_scroll_zoom() — заглушка встроенного зума
        │  • _snapshot_home()            — снимок пределов для сброса (C/polar/pie)
        │  • canvas.mpl_connect(...)     — scroll_event, pie hover/click
        ▼
плитка в QGridLayout (колонок 1–4) + tile._view_notify = view.on_tile_view_changed
```

Данные собирает `ChartsPage.build_data_from_results()` (`src/gui/pages/charts_page.py`), раздаются обеим страницам из `main_window.py`.

---

## 3. Категории диаграмм и поведение

Определены в `chart_interactions.py` (`ChartCategory`) и закреплены за 23 типами (Приложение А SPEC):

| Категория | Примеры | Зум | Особенности |
|---|---|---|---|
| **A** DECARTESIAN | harker, bland_altman, k1_k4, pca, dendrogram, parallel | обе оси | `sync_group` (harker — `harker-x:{oxide}`) |
| **B** CATEGORY_AXIS | bar, defect, rock_type, box_plot | только Y (числовая ось) | `_cat_bar_tiered`, группа `bar-y` |
| **C** EQUAL_ASPECT | qapf, tas, a_cn_k, feldspar_triangle, afm, mg_fe_al_ternary, sio2_k2o | единый фактор обеих осей | сохранение аспекта, snapshot; `min_range_fraction=0.25` для tas/sio2_k2o |
| **D** PIE | pie (rock_type при `chart_type="pie"`) | нет | hover %, explode, сброс формы |
| **E** POLAR | radar | через `r`-пределы | snapshot `rlim` |

### 3.1 Стандарты размеров отображения

Заданы в `chart_sizes.py` (`ChartSizeSpec`) для каждого из 23 типов. Решают
проблему «слишком широких» диаграмм: `FigureCanvasQTAgg` растягивает фигуру под
виджет, и без ограничений фигура с пропорцией 4:3 в режиме одной колонки
растягивалась почти до 4:1 и становилась нечитаемой. Плитка держит канвас в
рамках стандарта и центрирует его (`_ChartTile._apply_display_size`,
`aspect_for`).

Поля: `aspect` — целевой аспект (ширина/высота), `None` → «родной» аспект фигуры,
зажатый в `[min_aspect, max_aspect]`; `max_width` — предел ширины содержимого в
px (для квадратных/радиальных/тройных, `None` — на всю ширину ячейки);
`min_height`/`max_height` — границы высоты.

| Тип | Аспект | max_width | Назначение |
|---|---|---|---|
| bar | родной ≤2.6 | 1100 | групповые столбцы (категорий = образцов) |
| pie | 1.00 | 620 | круг — квадрат |
| defect | родной ≤2.6 | 900 | столбцы отклонений по оксидам |
| qapf | 1.00 | 620 | тройная классификационная |
| tas | 1.35 | 780 | классификационное поле |
| a_cn_k | 1.00 | 620 | тройная |
| heatmap | родной ≤2.4 | 1100 | матрица образцы×минералы |
| rock_type | родной ≤2.0 | 720 | столбцы или круг |
| feldspar_triangle | 1.00 | 620 | тройная |
| harker | родной ≤2.4 | 1100 | сетка подграфиков |
| afm | 1.00 | 620 | тройная |
| sio2_k2o | 1.15 | 720 | классификационное поле |
| bland_altman | 1.35 | 760 | рассеяние |
| correlation | 1.10 | 760 | матрица корреляций |
| k1_k4 | 1.67 | 860 | K-параметры |
| box_plot | родной ≤2.4 | 1100 | ящики по выборкам |
| radar | 1.00 | 620 | полярный |
| coefficient_heatmap | родной ≤3.0 | 1100 | низкая широкая карта |
| defect_accumulation | родной ≤2.6 | 1100 | накопление дефекта |
| pca_biplot | 1.25 | 820 | биплот |
| dendrogram | родной ≤2.4 | 1100 | дендрограмма |
| parallel_coordinates | родной ≤2.6 | 1100 | параллельные оси |
| mg_fe_al_ternary | 1.00 | 620 | тройная |

Минимальная ширина канваса — `MIN_CANVAS_WIDTH = 320`; целевой аспект
сохраняется (высота = ширина / аспект, зажата в границах).

---

## 4. Механика зума

### 4.1 Колесо и модификаторы

`_on_scroll` (`chart_grid.py:723`) определяет режим через `modifier_mode(event)`:

| Клавиши | `ModifierMode` | Действие |
|---|---|---|
| — | `ZOOM_XY` | зум обеих осей к курсору |
| Ctrl | `ZOOM_X` | зум только X |
| Ctrl+Shift | `ZOOM_Y` | зум только Y |
| Shift | `PAN_X` | панорамирование по X |

Вне области осей (`event.inaxes is None`) событие игнорируется. Категориальные оси (`is_categorical_axis`) не масштабируются.

### 4.2 Кнопки

```python
self._btn_zoom_out.clicked.connect(self._on_zoom_out)   # factor = 1 / step
self._btn_zoom_in.clicked.connect(self._on_zoom_in)      # factor = step
self._btn_reset.clicked.connect(self.reset_view)
```

Шаг — `DEFAULT_ZOOM_STEP` (×1.2), меняется из настроек (`zoom_step`), нормализуется `normalize_zoom_step`. Для категорий без зума кнопки скрываются (`_supports_zoom`, `_apply_spec`).

---

## 5. Математика (чистый модуль `zoom_math.py`)

- `zoom_lims(lims, anchor, factor, log=..., min_range_width=...)` — новые пределы так, чтобы `anchor` остался на месте; линейный и **лог**-случай (через десятичные логарифмы); защита от вырождения и `<=0`.
- `pan_lims(lims, fraction, log=...)` — сдвиг на долю диапазона.
- `anchor_fraction(anchor, lims)` / `value_at_fraction(fraction, lims)` — перевод «значение ↔ доля диапазона» (используется синхронизацией).
- `zoom_radial(rlim, factor, ...)` — зум для полярных через `r`-пределы.
- `modifier_mode(event)`, `is_categorical_axis(ax, which)`, `normalize_zoom_step(step)`.

Пример (линейная шкала, диапазон X `[0, 10]`, якорь `x=8`, фактор `1.25`):

```
new_lo = 8 - (8 - 0)*1.25   = -2
new_hi = 8 + (10 - 8)*1.25  = 10.5
```

Точка `x=8` остаётся на месте — «приближение к курсору».

---

## 6. Равноаспектные и полярные

- **C (EQUAL_ASPECT):** зум идёт единым фактором по обеим осям; `_keep_aspect` восстанавливает равенство масштабов после изменения пределов. Сброс — по `_snapshot_home()` (снимок исходных пределов), а не `relim+autoscale`, чтобы не потерять аспект.
- **E (POLAR, radar):** пределы меняются через `get_rlim/set_rlim`; сброс — по снимку `rlim`.
- Для категории C с общим доменом (TAS-поле) задан `min_range_fraction=0.25` — ограничивает чрезмерное приближение.

---

## 7. Круговые (pie)

Подключаются только для `ChartCategory.PIE` (`_connect_pie_events`, `chart_grid.py:184`), cids хранятся в `self._cids` с парным `disconnect_events`:

- **Hover** (`_on_hover`) — в `toolbar.set_message` выводится `"<label> — <pct>%"` по текущему сегменту.
- **Клик** (`_on_click`) — explode: сегмент сдвигается на `0.1` радиуса по биссектрисе; повторный клик возвращает на место.
- **Сброс** (`_reset_pie`) — все сегменты к базовым центрам; вызывается из `_restore_view`.
- Колесо над pie — no-op; zoom/pan-инструменты тулбара дизейблятся.

> Особенность рендерера: `create_figure` (через `plt.subplots`) создаёт первую ось, а `fig.add_subplot(111)` — вторую; сегменты (`Wedge`) лежат на дополнительной оси. Поиск сегментов — `_get_wedges(ax)` по классу патча, а не по фиксированному индексу.

---

## 8. Синхронизированный зум

Реализован в §9 SPEC.

- **Группы** — по ключу `sync_group` из спецификации: `bar-y`, `ternary-100`, `tas-field`, `samples`, `harker-x:{oxide}`, `ba`, `k-params`, `pca`. Динамическая часть `{oxide}` резолвится на стороне сетки.
- **Переключатель** — «Синхронизировать зум» в панели `MultiChartView` (по умолчанию выключен).
- **Трансляция только через сетку** (`on_tile_view_changed`) — плитки не знают друг о друге; при выключенном чекбоксе поведение автономно.
- **Пропорционально** (A/B/E): передаются фактор и доли якоря (`anchor_frac_x/y`); каждая плитка применяет их к своим пределам.
- **Абсолютно** (C с общим доменом): передаются точные пределы (плюс флаги шкалы lin/log — оси с другой шкалой пропускаются).
- **Пан** — смещение в долях диапазона.
- **Защита от циклов** — флаг `MultiChartView._syncing` на время трансляции; повторные оповещения подавляются.
- **Батч** — мутация всех участников, затем один `draw_idle()` на канвас.

---

## 9. Память, перестройка, экспорт

- `_release_tiles` (`chart_grid.py:1004`) закрывает фигуры через `plt.close` перед заменой; `_clear_grid` (`:1122`) — только разметка, живые плитки переиспользуются при смене числа колонок (`_reflow_tiles`, `:998`). При reflow виджеты отсоединяются через `_clear_grid(keep=tiles)` **без** `deleteLater()` — иначе отложенное удаление уничтожало бы переиспользуемые плитки, и при смене колонок падало `RuntimeError: wrapped C/C++ object ... has been deleted`.
- Экспорт плитки (`export_tile`, `:1017`) сохраняет фигуру в текущем состоянии (зум/пан не сбрасываются); формат по расширению (PNG/PDF/SVG). `export_all` (`:1041`) сохраняет все плитки в папку PNG. `export_all_pdf` (`:1073`) пишет все плитки в один многостраничный PDF (`_export_all_pdf_to`, по странице на плитку, текущий вид).

---

## 10. Валидация

Корневой GUI smoke-тест (`gui_full_smoke.py`, offscreen) — все PASS, включая пункты этапов 1–5:

```
PASS multi-chart grid (ChartsPage/OutputPage): 4 tiles, columns reflow, wheel+anchor zoom, reset
PASS size standards: per-type canvas aspect and width caps
PASS registry: 23 type_ids, KeyError/ValueError on unknown
PASS pie: wheel no-op, buttons hidden, reset visible, toolbar tools disabled
PASS pie: hover %, click explode/return, reset restores shape
PASS modifiers: wheel XY, Ctrl->zoom_x, Ctrl+Shift->zoom_y, Shift->pan_x
PASS zoom step from settings: applied instantly to live tile, wheel uses new factor
PASS grid group ops: zoom_all skips pie, reset_all restores all
PASS sync: bar-y group proportional, isolation, cycle guard
PASS export: multi-page PDF with 2 pages
ALL GUI SMOKE TESTS PASSED
```

Полный тест-сьют: **1192 passed, 5 skipped** (включая `tests/test_chart_sizes.py`). Статический анализ (`ruff`, `select=E,F,I,N,W,UP`) — чисто.

Примечания:
- GUI-проверки идут в offscreen (`QT_QPA_PLATFORM=offscreen`); события синтезируются объектами с полями `inaxes/xdata/ydata/step` и MouseEvent.
- Отдельный `verify_sync_stage5.py` покрывает синхронизацию: изоляция, пропорциональность, цикл-guard, абсолютный синк, пан в долях, кросс-групповая изоляция.
- Ручная проверка: построить 2–4 диаграммы, покрутить колесо над графиком, проверить Ctrl/Ctrl+Shift/Shift, кнопки, «По умолчанию», «руку», чекбокс синхронизации.

---

## 11. Ограничения и граничные случаи

| Случай | Поведение |
|---|---|
| Колесо над pie | No-op |
| Категориальная ось (bar X и т.п.) | Не масштабируется |
| Лог-шкала | Пересчёт в `log10`, якорь сохраняется; при `lo/hi/anchor <= 0` — линейное ветвление |
| Курсор вне осей | Событие игнорируется |
| Встроенный инструмент «лупа» | Встроенный scroll-зум отключён — сдвоенного зума нет |
| Смена числа колонок | Только переразметка, зум плиток сохраняется |
| Широкая ячейка (1 колонка) | Канвас держится в стандарте типа: целевой аспект + `max_width`, центрируется; диаграмма не растягивается |
| Узкая ячейка (<320 px) | Канвас не уже `MIN_CANVAS_WIDTH` — появляется горизонтальная прокрутка |
| Сброс | Для C/polar/pie — по snapshot; для остальных — `relim + autoscale` |
| Разные шкалы у синхронизируемых осей | Ось с несовпадающей шкалой (lin/log) при абсолютной синхронизации пропускается |

---

## 12. Отложено (SPEC §20)

Групповой экспорт в многостраничный PDF **реализован** (`export_all_pdf`, кнопка «Экспорт всех в PDF»). Остальные пункты вынесены в `CHART_INTERACTIONS_TODO.md`:

| Функция | Причина |
|---|---|
| Drill-down по срезу pie | Нужна модель данных второго уровня в `ChartData` |
| Resize плитки колесом для pie | Спорная ценность |
| Подпись текущего поля TAS/QAPF при зуме | Нужно обратное преобразование координат в рендерерах |
| Индикатор множителя зума («×1.2») | Низкая ценность, риск рассинхрона с реальными пределами |

---

## 13. Карта кода (актуальные ориентиры)

| Тема | Место |
|---|---|
| Реестр спецификаций, категории, `sync_group` | `src/gui/widgets/chart_interactions.py` |
| Реестр стандартов размеров (аспект, `max_width`) | `src/gui/widgets/chart_sizes.py` |
| Применение стандарта размера, центрирование канваса | `_ChartTile._apply_display_size`, `resizeEvent`, `chart_grid.py:190-224` |
| Чистая математика пределов | `src/gui/widgets/zoom_math.py` |
| Плитка: канвас, тулбар, spec, snapshot | `_ChartTile.set_figure`, `chart_grid.py:148` |
| Круговые события (hover/click/reset) | `chart_grid.py:184-274` |
| Зум / применение режима | `zoom`, `_apply_zoom`, `chart_grid.py:395-518` |
| Пан X | `pan_x`, `chart_grid.py:529` |
| Синхронизация (плитка) | `apply_synced`, `chart_grid.py:574` |
| Сброс вида | `_restore_view`, `chart_grid.py:676` |
| Обработчик колеса | `_on_scroll`, `chart_grid.py:723` |
| Сетка: чекбокс синка, групповые операции | `MultiChartView`, `chart_grid.py:748` |
| Трансляция синхронизации | `on_tile_view_changed`, `chart_grid.py:892` |
| Построение сетки | `render`, `chart_grid.py:951` |
| Экспорт | `export_tile`/`_export_tile`/`export_all`/`export_all_pdf`, `chart_grid.py:1017-1116` |
| Сборка `ChartData` | `src/gui/pages/charts_page.py` |
| Раздача данных страницам | `src/gui/main_window.py` |
