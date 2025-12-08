import logging
import threading
from datetime import UTC, datetime
from typing import ClassVar, Self, TypedDict, override

from discord import Color, Embed, SyncWebhook

from app.core.config import get_config


class DiscordPayload(TypedDict):
    """Type definition for the data passed to the worker thread."""

    embed: Embed | None
    content_lines: list[str] | None


class DiscordWebhookHandler(logging.Handler):
    MAX_EMBED_DESCRIPTION: ClassVar[int] = 4096
    MAX_CONTENT_LENGTH: ClassVar[int] = 2000
    DECORATORS_LEN: ClassVar[int] = 8

    COLOR_MAP: ClassVar[dict[int, Color]] = {
        logging.NOTSET: Color.default(),
        logging.DEBUG: Color.blue(),
        logging.INFO: Color.green(),
        logging.WARNING: Color.yellow(),
        logging.ERROR: Color.red(),
        logging.CRITICAL: Color.red(),
    }

    def __init__(self, webhook_url: str) -> None:
        super().__init__()
        self.webhook_url: str = webhook_url

    @classmethod
    def from_config(cls) -> Self:
        config = get_config()
        webhook_url = config.general.discord_webhook
        if not webhook_url:
            raise ValueError("Discord webhook URL not configured")
        return cls(webhook_url=webhook_url)

    @override
    def emit(self, record: logging.LogRecord) -> None:
        """
        Main Thread: Captures context and formats message.

        Then spawns a thread for network I/O.
        """
        try:
            # 1. Format immediately to capture ContextVars and Tracebacks
            formatted_message = self.format(record)

            # 2. Capture metadata immediately
            footer_text = self._format_footer(record)

            # 3. Prepare payload
            payload: DiscordPayload = {"embed": None, "content_lines": None}

            if len(formatted_message) > self.MAX_EMBED_DESCRIPTION:
                payload["content_lines"] = self._prepare_content_chunks(record, formatted_message, footer_text)
            else:
                payload["embed"] = self._prepare_embed(record, formatted_message, footer_text)

            # 4. Offload to thread
            # We pass 'record' so the worker can call handleError if the network fails
            t = threading.Thread(
                target=self._worker_send,
                kwargs={"payload": payload, "record": record},
                daemon=True,
            )
            t.start()
        except Exception:
            self.handleError(record)

    def _worker_send(self, payload: DiscordPayload, record: logging.LogRecord) -> None:
        """Background Thread: Performs blocking network I/O."""
        try:
            webhook = SyncWebhook.from_url(self.webhook_url)

            if payload["embed"] is not None:
                webhook.send(embed=payload["embed"])

            if payload["content_lines"] is not None:
                for line in payload["content_lines"]:
                    webhook.send(content=line)

        except Exception:
            # Call handleError so the logger system knows something went wrong
            self.handleError(record)

    def _format_footer(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created, UTC)
        return f"{dt.strftime('%Y-%m-%d %H:%M:%S UTC')} - {record.processName} - {record.funcName}:{record.lineno}"

    def _prepare_embed(self, record: logging.LogRecord, msg: str, footer: str) -> Embed:
        embed = Embed(title=record.name, description=msg, color=self.COLOR_MAP.get(record.levelno))
        embed.set_footer(text=footer)
        return embed

    def _prepare_content_chunks(self, record: logging.LogRecord, msg: str, footer: str) -> list[str]:
        # Header
        base_content = f"[{record.levelname}] {footer} - {record.name}:\n"
        chunks = [base_content]

        # Body Splitting
        available = self.MAX_CONTENT_LENGTH - self.DECORATORS_LEN
        lines = msg.splitlines()
        current = ""

        for line in lines:
            if len(current) + len(line) + 1 > available:
                chunks.append(f"```\n{current}\n```")
                current = line
            else:
                if current:
                    current += "\n"
                current += line

        if current:
            chunks.append(f"```\n{current}\n```")

        return chunks
