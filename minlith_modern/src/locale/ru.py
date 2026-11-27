"""Russian locale — все строки интерфейса на русском."""

# ── CLI ──
CLI_DESCRIPTION = "MINLITH Modern — Нормативный минералогический расчёт"
CLI_CALC_HELP = "Рассчитать минеральный состав"
CLI_INFO_HELP = "Показать информацию о файле"
CLI_VALIDATE_HELP = "Проверить входные данные"
CLI_CHART_HELP = "Создать диаграмму"
CLI_REPORT_HELP = "Создать отчёт"
CLI_GUI_HELP = "Запустить графический интерфейс"
CLI_INPUT_HELP = "Входные файлы: .xlsx, .xls, .csv, .zip"
CLI_OUTPUT_HELP = "Путь для выходного файла"
CLI_FORMAT_HELP = "Формат вывода (определяется по расширению -o)"
CLI_TEMPLATE_HELP = "Шаблон отчёта"
CLI_CHART_TYPE_HELP = (
    "Тип диаграммы: bar, pie, acnk, defect, heatmap, box_plot, rock_type, "
    "pca_biplot"
)
CLI_DPI_HELP = "Разрешение изображения (DPI)"
CLI_INTERACTIVE_HELP = "Экспорт в интерактивный HTML (Plotly)"
CLI_VERSION = "0.2.0"

# CLI messages
MSG_LOADED = "Загружено %d образцов из %s"
MSG_NO_SAMPLES = "ВНИМАНИЕ: Образцы не найдены в %s"
MSG_CALCULATED = "  %s -> %s   (F=%.3f, Ab=%.1f%%)"
MSG_EXPORTED = "\nЭкспортировано %d результатов в %s"
MSG_NO_RESULTS = "Нет результатов для экспорта."
MSG_FILE_NOT_FOUND = "ОШИБКА: Файл не найден: %s"
MSG_CHART_EXPORTED = "Диаграмма экспортирована: %s"
MSG_INTERACTIVE_EXPORTED = "Интерактивная диаграмма экспортирована: %s"
MSG_REPORT_EXPORTED = "Отчёт экспортирован: %s"
MSG_VALIDATION_PASSED = "Проверка пройдена"
MSG_VALIDATION_ERRORS = "Найдено ошибок: %d"
MSG_AVAILABLE_CHARTS = "Доступные диаграммы:"
MSG_AVAILABLE_TEMPLATES = "Доступные шаблоны:"
MSG_UNKNOWN_CHART = "Неизвестный тип диаграммы: %s"
MSG_FALLBACK_CHART = "Нет интерактивной версии для '%s', используется matplotlib"
MSG_DB_SAVED = "Сохранено в БД"

# ── Validation warnings ──
WARN_LOW_SUM = "Сумма оксидов %.2f%% ниже допустимого диапазона 98.0-102.0%%"
WARN_HIGH_SUM = "Сумма оксидов %.2f%% выше допустимого диапазона 98.0-102.0%%"
WARN_NEGATIVE = "Отрицательное значение %s: %.2f%%"
WARN_ZERO_SUM = "Сумма оксидов равна нулю"
WARN_MISSING_OXIDES = "Отсутствуют основные оксиды"

# ── Error messages ──
ERR_FILE_NOT_FOUND = "Файл не найден. Проверьте путь и попробуйте снова."
ERR_INVALID_FORMAT = "Неподдерживаемый формат. Используйте .xlsx, .xls или .csv."
ERR_NO_SAMPLES = "Образцы не найдены в файле."
ERR_CALCULATION = "Ошибка расчёта. Проверьте входные данные."
ERR_DB = "Ошибка базы данных. Перезапустите приложение."
ERR_EXPORT = "Ошибка экспорта. Проверьте права на запись."
ERR_MEMORY = "Недостаточно памяти. Уменьшите размер пакета."
ERR_TIMEOUT = "Расчёт превысил время ожидания. Попробуйте с меньшим количеством образцов."

# ── GUI labels ──
GUI_TITLE = "MINLITH Modern v0.2.0 — Нормативная минералогия"
GUI_WELCOME = "Добро пожаловать в MINLITH Modern"
GUI_WELCOME_DESC = "Загрузите файлы .xlsx/.csv для начала работы"
GUI_SIDEBAR_WELCOME = "Начало"
GUI_SIDEBAR_FILES = "Файлы"
GUI_SIDEBAR_INPUT = "Ввод"
GUI_SIDEBAR_RESULTS = "Результаты"
GUI_SIDEBAR_CHARTS = "Диаграммы"
GUI_SIDEBAR_REPORTS = "Отчёты"
GUI_SIDEBAR_HISTORY = "История"
GUI_SIDEBAR_SETTINGS = "Настройки"
GUI_SIDEBAR_LOGS = "Журнал"

# Files page
GUI_IMPORT_BTN = "Импорт файлов"
GUI_IMPORT_CSV = "Импорт CSV"
GUI_DRAG_DROP = "Перетащите файлы сюда"
GUI_RECENT = "Недавние файлы"

# Input page
GUI_CALCULATE_BTN = "Рассчитать (F5)"
GUI_SAMPLE_NAME = "Название образца"

# Results page
GUI_RESULTS_TITLE = "Результаты расчёта"

# History page
GUI_HISTORY_SEARCH = "Поиск образцов..."
GUI_HISTORY_REFRESH = "Обновить"
GUI_HISTORY_DELETE = "Удалить выбранное"
GUI_HISTORY_EXPORT = "Экспорт CSV"
GUI_HISTORY_RECORDS = "%d записей"
GUI_HISTORY_DELETE_CONFIRM = "Удалить %d записей?"
GUI_HISTORY_EXPORT_DONE = "Экспортировано %d записей"

# Settings page
GUI_SETTINGS_TITLE = "Настройки"

# Charts page
GUI_CHARTS_TITLE = "Диаграммы"

# Reports page
GUI_REPORTS_TITLE = "Отчёты"

# ── Report templates ──
REPORT_BRIEF = "Краткий"
REPORT_STANDARD = "Стандартный"
REPORT_FULL = "Полный"
REPORT_TITLE = "Отчёт MINLITH"
REPORT_SAMPLES = "Образцы"
REPORT_INPUT = "Входные данные"
REPORT_MINERALS = "Минеральный состав"
REPORT_COEFFICIENTS = "Коэффициенты"
REPORT_DEFECT = "Дефект (остатки оксидов)"
REPORT_PARAMETERS = "Параметры"

# ── Chart titles ──
CHART_BAR_TITLE = "Минеральный состав"
CHART_PIE_TITLE = "Минералы (круговая диаграмма)"
CHART_ACNK_TITLE = "Диаграмма A-CN-K"
CHART_HEATMAP_TITLE = "Тепловая карта минералов"
CHART_ROCK_TYPE_TITLE = "Распределение типов пород"
CHART_DEFECT_TITLE = "Дефект"
