"""Core application loop for the concierge bot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from .config import Settings


ResponseHandler = Callable[[str], str]


@dataclass
class BotCommand:
    """A simple representation of a bot command."""

    name: str
    description: str
    handler: ResponseHandler


class BotApp:
    """Minimal interactive command-line bot."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._commands: Dict[str, BotCommand] = {}
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        self.register_command(
            "help",
            "Show this help message.",
            self._handle_help,
        )
        self.register_command(
            "about",
            "Learn what this bot can do.",
            self._handle_about,
        )

    def register_command(
        self, name: str, description: str, handler: ResponseHandler
    ) -> None:
        """Register a new bot command."""

        key = name.strip().lower()
        command = BotCommand(name=name, description=description, handler=handler)
        self._commands[key] = command

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def run(self) -> None:
        """Run the interactive bot loop."""

        print(f"{self.settings.greeting} I am {self.settings.bot_name}.")
        print("Type 'help' to see available commands or 'exit' to quit.")

        while True:
            try:
                message = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting. See you next time!")
                break

            if not message:
                continue

            lowered = message.lower()
            if lowered in {"exit", "quit"}:
                print("Goodbye!")
                break

            print(self.handle_message(message))

    def handle_message(self, message: str) -> str:
        """Produce a response for the provided message."""

        normalized = message.strip().lower()
        if not normalized:
            return "Please enter a command or type 'help' to see the options."

        command = self._commands.get(normalized)
        if command is not None:
            return command.handler(message)

        return (
            "I'm not sure how to help with that. Type 'help' to see the available "
            "commands."
        )

    # ------------------------------------------------------------------
    # Built-in command handlers
    # ------------------------------------------------------------------
    def _handle_help(self, _: str) -> str:
        """Return a formatted description of all registered commands."""

        lines = ["Available commands:"]
        for command in sorted(
            self._commands.values(), key=lambda c: c.name.lower()
        ):
            lines.append(f"- {command.name}: {command.description}")
        lines.append("Type 'exit' or press Ctrl+C to quit.")
        return "\n".join(lines)

    def _handle_about(self, _: str) -> str:
        """Return a short description of the bot."""

        return (
            "This is a lightweight concierge bot that demonstrates how to "
            "structure a command-line application."
        )


__all__ = ["BotApp"]

