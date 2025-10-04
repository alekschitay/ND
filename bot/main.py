from .app import BotApp
from .config import Settings


def main() -> None:
    """Entrypoint for running the bot application."""
    settings = Settings.from_env()
    app = BotApp(settings=settings)
    app.run()


if __name__ == "__main__":
    main()
