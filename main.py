"""Точка входа в десктопное приложение мониторинга рынка криптовалют."""

from __future__ import annotations

import ctypes
import sys

from gui import CryptoMonitorApp


def _set_windows_app_id() -> None:
    """Регистрирует AppUserModelID в Windows, чтобы иконка приложения отображалась в панели задач."""
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "antigravity.cryptomonitor.desktop.1"
            )
        except Exception:
            pass


def main() -> None:
    """Запуск главного окна CustomTkinter с подключенным бэкендом."""
    _set_windows_app_id()
    app = CryptoMonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
