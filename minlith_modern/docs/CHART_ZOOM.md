# Приближение / отдаление диаграмм в GUI — данные для обсуждения

> Дата: 2026-09-16
> Модуль: `minlith_modern/src/gui/widgets/chart_grid.py`
> Страницы: «Диаграммы» и «Вывод» (`ChartsPage`, `OutputPage`) — обе используют общий виджет `MultiChartView`.

---

## 1. Что реализовано

| Возможность | Способ | Где в коде |
|---|---|---|
| Приблизить / отдалить | Кнопки «Приблизить» / «Отдалить» (шаг ×1.25 вокруг центра) | `chart_grid.py:58-74` |
| Приблизить / отдалить | Колесо мыши над канвасом (привязка к точке под курсором) | `chart_grid.py:114, 172-177` |
| Сброс к исходному размеру | Кнопка «По умолчанию» (relim + autoscale) для каждой диаграммы | `chart_grid.py:70-74, 179-189` |
| Панорамирование (двигание) | Встроенная панель matplotlib («hand») + rect-зум линзой | `chart_grid.py:117-122` |
| Экспорт текущего вида | Кнопка «Экспорт» сохраняет фигуру как есть (без сброса зума) | `chart_grid.py:354-373` |

Ключевая смена подхода: диаграммы больше **не рендерятся в статичные PNG** (`QLabel` + `QPixmap`), а встраиваются как **живые канвасы matplotlib QtAgg**. Это дало зум/пан нативно, в любом разрешении, без пересоздания изображения.

---

## 2. Архитектура и поток данных

```
Пользователь выбирает чекбоксы → «Построить выбранные»
        │
        ▼
MultiChartView.render()          chart_grid.py:291-330
        │  для каждой выбранной диаграммы:
        ▼
chart.render(ChartData)  →  matplotlib Figure
        │
        ▼
_ChartTile.set_figure(idx, fig, title)   chart_grid.py:104-125
        │  создаёт:
        │    • FigureCanvasQTAgg(fig)        — живой канвас
        │    • NavigationToolbar2QT(canvas)  — панель (zoom/pan/home/save)
        │    • canvas.mpl_connect("scroll_event", self._on_scroll) — колесо
        ▼
Плитка добавлена в QGridLayout (число колонок 1–4, QSpinBox)   chart_grid.py:220-227, 320-322
```

Данные для диаграмм собирает `ChartsPage.build_data_from_results()` (`src/gui/pages/charts_page.py:37-80`) и через `set_data()` раздаёт обеим страницам (`src/gui/main_window.py:212-214, 238-240`).

---

## 3. Механизм зума кнопками

Метод `zoom()` проходит по всем осям фигуры и масштабирует пределы. По умолчанию якорь — центр осей.

```python
# chart_grid.py:127-154
def zoom(self, factor: float, anchor: tuple | None = None) -> None:
    if self._fig is None or self._canvas is None:
        return
    for ax in self._fig.axes:
        try:
            xlog = ax.get_xscale() == "log"
            ylog = ax.get_yscale() == "log"
            ax_anchor = (float(anchor[0]), float(anchor[1])) if anchor is not None else None
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            cx = (xlim[0] + xlim[1]) / 2.0
            cy = (ylim[0] + ylim[1]) / 2.0
            if ax_anchor is not None:
                cx = ax_anchor[0]
                cy = ax_anchor[1]
            new_xlim = self._zoom_lims(xlim, cx, factor, log=xlog)
            new_ylim = self._zoom_lims(ylim, cy, factor, log=ylog)
            ax.set_xlim(*new_xlim)
            ax.set_ylim(*new_ylim)
        except Exception:
            continue
    self._canvas.draw_idle()
```

Подписи и привязка кнопок:

```python
# chart_grid.py:58-74
self._btn_zoom_out = QPushButton("Отдалить")
self._btn_zoom_out.clicked.connect(lambda: self.zoom(1 / self.ZOOM_STEP))  # ×0.8
self._btn_zoom_in = QPushButton("Приблизить")
self._btn_zoom_in.clicked.connect(lambda: self.zoom(self.ZOOM_STEP))       # ×1.25
self._btn_reset = QPushButton("По умолчанию")
self._btn_reset.clicked.connect(self.reset_view)
```

Шаг зума: `ZOOM_STEP = 1.25` (`chart_grid.py:38`).

---

## 4. Математика масштабирования (якорь остаётся на месте)

`_zoom_lims()` считает новые пределы так, чтобы точка `anchor` не смещалась. Линейный случай:

```python
# chart_grid.py:156-170
new_lo = anchor - (anchor - lo) * factor
new_hi = anchor + (hi - anchor) * factor
# то же для двух осей; лог-шкала считается в десятичных логарифмах:
lo_l = math.log10(lo); hi_l = math.log10(hi); a_l = math.log10(anchor)
new_lo = 10 ** (lo_l - (a_l - lo_l) * factor)
new_hi = 10 ** (hi_l + (hi_l - a_l) * factor)
```

Пример для обсуждения: диапазон X `[0, 10]`, якорь `x=8`, `factor=1.25`:

```
new_lo = 8 - (8 - 0)*1.25   = 8 - 10   = -2
new_hi = 8 + (10 - 8)*1.25  = 8 + 2.5  = 10.5
```

Точка под курсором `x=8` остаётся в новой области ровно на месте — это и есть «приближение к курсору».

---

## 5. Колесо мыши

Подключение события канваса:

```python
# chart_grid.py:114
canvas.mpl_connect("scroll_event", self._on_scroll)
```

Обработчик (вверх — приблизить, вниз — отдалить; якорь — позиция курсора в координатах данных):

```python
# chart_grid.py:172-177
def _on_scroll(self, event) -> None:
    if event.inaxes is None:
        return
    factor = self.ZOOM_STEP ** event.step if event.step > 0 else (1 / self.ZOOM_STEP) ** abs(event.step)
    self.zoom(factor, anchor=(event.xdata, event.ydata))
```

Важно: выход за границы осей (`event.inaxes is None`) игнорируется — колёсико на пустом поле канваса ничего не делает.

---

## 6. Сброс к исходному размеру («По умолчанию»)

Для каждой отдельной диаграммы вызывается `relim()` (пересчёт пределов по данным) и `autoscale_view()`:

```python
# chart_grid.py:179-189
def reset_view(self) -> None:
    if self._fig is None or self._canvas is None:
        return
    try:
        for ax in self._fig.axes:
            ax.relim()
            ax.autoscale_view()
    except Exception:
        pass
    self._canvas.draw_idle()
```

Сброс локальный — не затрагивает другие диаграммы сетки.

---

## 7. Управление памятью

Фигуры закрываются при перестроении сетки, чтобы не копить фигуры в реестре pyplot:

```python
# chart_grid.py:342-352
def _release_tiles(self) -> None:
    """Закрыть matplotlib-фигуры плиток перед заменой (освобождение памяти)."""
    import matplotlib.pyplot as plt
    for tile in self._tiles:
        fig = tile.figure
        if fig is not None:
            try:
                plt.close(fig)
            except Exception:
                continue
    self._tiles.clear()
```

`_clear_grid()` (`chart_grid.py:405-410`) при этом фигуры не закрывает — перестройка сетки колонок (`_reflow_tiles`, `chart_grid.py:332-340`) живые плитки переиспользует.

---

## 8. Экспорт текущего вида

Экспорт плитки сохраняет фигуру **в текущем состоянии** (зум/пан не сбрасываются):

```python
# chart_grid.py:366-371
if tile.figure is not None:
    tile.figure.savefig(path, format=fmt, dpi=150, bbox_inches="tight")
elif self._data is not None:
    chart.export(self._data, path, fmt=fmt)
```

Формат выбирается по расширению файла (PNG/PDF/SVG), разбор — `chart_grid.py:365`.

---

## 9. Валидация (результаты проверок)

### Корневой GUI smoke-тест (`gui_full_smoke.py`, offscreen)
Все проверки прошли:

```
PASS window+pages
PASS page cycling
PASS settings->clean rebuild: CleanEngineAlgorithm
PASS settings->stub rebuild: TheoryAlgorithm
PASS input->calculate->results  | TYPE_2 q=33.98
PASS results/charts/output/reports wiring
PASS multi-chart grid (ChartsPage): 4 tiles, columns reflow, wheel+anchor zoom, reset
PASS multi-chart grid (OutputPage): 4 tiles, columns reflow, wheel+anchor zoom, reset
PASS batch dialog results: 3
PASS parallel worker finished, results: [12]
PASS worker _calc_single clean-mode result q=33.98
ALL GUI SMOKE TESTS PASSED
```

Проверяемые утверждения (фрагмент):

```python
tile.zoom(1.25)
assert ax.get_xlim() != x0 or ax.get_ylim() != y0        # зум меняет пределы
tile.zoom(1.25, anchor=(px, py))                          # якорь под курсором
assert abs(ax.get_xlim()[0] - newlo[0]) < 1e-9            # якорь не сдвинулся
tile._on_scroll(Ev())                                     # колесо: step=1 → зум
assert ax.get_xlim() != xb                                # пределы изменились
```

### Полный тест-сьют
```
1066 passed, 5 skipped, 10 warnings
```

### Замечания по проверкам
- Все проверки GUI — в offscreen-режиме (`QT_QPA_PLATFORM=offscreen`), т.е. корректны без реального дисплея; события колеса мыши симулируются через объект события с полями `inaxes/xdata/ydata/step`.
- Проверка «человеком»: построить 2–4 диаграммы, навести курсор на график и крутануть колесо; нажать кнопки отдалить/приблизить; «По умолчанию» возвращает вид; инструмент «рука» двигает область.

---

## 10. Ограничения и граничные случаи

| Случай | Поведение | Детали |
|---|---|---|
| Колесо над диаграммами без обычных осей (круговые, тройные) | Зум применяется к пределам осей; при исключениях ось пропускается (`except: continue`, `chart_grid.py:152-153`) | Круговая диаграмма автоматически сохраняет масштабирование, т.к. аспект у неё equal |
| Лог-шкала | Пересчёт в `log10`, якорь сохраняется | `chart_grid.py:160-167`; при `lo<=0 или hi<=0 или anchor<=0` — линейное ветвление |
| Курсор вне области данных | Событие игнорируется | `chart_grid.py:174-175` |
| Активен инструмент «лупа» панели matplotlib | Возможен сдвоенный зум (наш обработчик + встроенный scroll-зум) | Когда zoom-tool активен; в выключенном состоянии работает только наш обработчик |
| Диапазоны с NaN (например, часть Harker-поля пустая) | `set_xlim/set_ylim` применяется к пределам, построение не ломается | - |
| Смена числа колонок сетки | Только переразметка, зум каждой плитки сохраняется | `_reflow_tiles`, `chart_grid.py:332-340` |
| Сброс после зума | «По умолчанию» возвращает к autoscale данных | `reset_view`, `chart_grid.py:179-189` |

---

## 11. Быстродействие и дальнейшие улучшения

- Текущая стоимость: одна перерисовка канвасов `draw_idle()` на событие; при сетке 4–8 плиток — приемлемо.
- Возможные улучшения (если решат обсуждать):
  1. Ctrl-колесо — горизонтальное панорамирование (сейчас нет).
  2. Уменьшить шаг колёсика при зажатой клавише — плавный зум.
  3. Показывать выбранный масштаб (например, подписи «×1.25», «×2») и кнопку «по умолчанию» в процентах.
  4. Вынести параметр `ZOOM_STEP` в настройки.
  5. При очень большом числе выбранных диаграмм перейти на отложенную (ленивую) отрисовку вкладок.

---

## 12. Состав файла для обсуждения (быстрая карта ссылок)

| Тема | Файл:строка |
|---|---|
| Шаг зума | `src/gui/widgets/chart_grid.py:38` |
| Кнопки «Отдалить/Приблизить/По умолчанию» | `src/gui/widgets/chart_grid.py:58-74` |
| Создание живого канваса + подсоединение колеса | `src/gui/widgets/chart_grid.py:109-125` |
| Зум с якорем | `src/gui/widgets/chart_grid.py:127-154` |
| Математика пределов (линейная и лог) | `src/gui/widgets/chart_grid.py:156-170` |
| Обработчик колеса мыши | `src/gui/widgets/chart_grid.py:172-177` |
| Сброс к исходному виду | `src/gui/widgets/chart_grid.py:179-189` |
| Построение сетки | `src/gui/widgets/chart_grid.py:291-330` |
| Освобождение фигур | `src/gui/widgets/chart_grid.py:342-352` |
| Экспорт текущего вида | `src/gui/widgets/chart_grid.py:354-373` |
| Сборка ChartData | `src/gui/pages/charts_page.py:37-80` |
| Раздача данных страницам | `src/gui/main_window.py:212-214` |