"""Error handling — retry decorator, safe_execute, русские сообщения."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Декоратор: повтор при ошибке с экспоненциальной задержкой."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        wait = delay * (2 ** (attempt - 1))
                        logger.warning("Повтор %d/%d для %s через %.1fs: %s",
                                       attempt, max_attempts, func.__name__, wait, e)
                        time.sleep(wait)
                    else:
                        logger.error("Все %d попыток неудачны для %s: %s",
                                     max_attempts, func.__name__, e)
            raise last_exc  # type: ignore
        return wrapper  # type: ignore
    return decorator


def safe_execute(func: F, *args, default=None, log_error: bool = True, **kwargs) -> Any:
    """Безопасное выполнение функции, возвращает default при ошибке."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error("safe_execute: ошибка в %s: %s", func.__name__, e)
        return default


USER_MESSAGES = {
    "file_not_found": "Файл не найден. Проверьте путь и попробуйте снова.",
    "invalid_format": "Неподдерживаемый формат. Используйте .xlsx, .xls или .csv.",
    "no_samples": "Образцы не найдены в файле.",
    "calculation_error": "Ошибка расчёта. Проверьте входные данные.",
    "db_error": "Ошибка базы данных. Перезапустите приложение.",
    "export_error": "Ошибка экспорта. Проверьте права на запись.",
    "memory_error": "Недостаточно памяти. Уменьшите размер пакета.",
    "timeout": "Расчёт превысил время ожидания. Попробуйте с меньшим количеством образцов.",
}


def get_user_message(error_type: str, detail: str = "") -> str:
    """Получить понятное сообщение об ошибке."""
    msg = USER_MESSAGES.get(error_type, f"Неожиданная ошибка: {detail}")
    if detail:
        msg += f"\n\nПодробности: {detail}"
    return msg
