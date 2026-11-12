"""Точка входа в десктопное приложение мониторинга рынка криптовалют."""

from gui import CryptoMonitorApp


def main() -> None:
    """Запуск главного окна CustomTkinter."""
    app = CryptoMonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
