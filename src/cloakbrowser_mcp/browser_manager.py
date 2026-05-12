"""Browser lifecycle manager for CloakBrowser MCP Server."""

import asyncio
import base64
import io
import json
import logging
from typing import Optional

from cloakbrowser import launch, launch_async, launch_context, launch_context_async

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages a single CloakBrowser instance and its pages."""

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        self._console_logs: list[str] = []
        self._lock = asyncio.Lock()

    async def ensure_browser(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        humanize: bool = False,
        user_agent: Optional[str] = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        locale: Optional[str] = None,
        fingerprint_seed: Optional[str] = None,
        geoip: bool = False,
    ):
        """Launch browser if not already running."""
        async with self._lock:
            if self._browser is not None:
                return

            args = []
            if fingerprint_seed:
                args.append(f"--fingerprint={fingerprint_seed}")

            launch_kwargs = {
                "headless": headless,
            }
            if proxy:
                launch_kwargs["proxy"] = proxy
            if humanize:
                launch_kwargs["humanize"] = humanize
            if args:
                launch_kwargs["args"] = args
            if geoip:
                launch_kwargs["geoip"] = geoip

            self._browser = await launch_async(**launch_kwargs)

            context_kwargs = {
                "viewport": {"width": viewport_width, "height": viewport_height},
            }
            if user_agent:
                context_kwargs["user_agent"] = user_agent
            if locale:
                context_kwargs["locale"] = locale

            self._context = await self._browser.new_context(**context_kwargs)
            self._page = await self._context.new_page()

            # Set up console log capture
            self._page.on("console", self._on_console)

            logger.info("Browser launched successfully")

    def _on_console(self, msg):
        """Capture console messages."""
        self._console_logs.append(f"[{msg.type}] {msg.text}")
        # Keep only last 500 messages
        if len(self._console_logs) > 500:
            self._console_logs = self._console_logs[-500:]

    @property
    def page(self):
        return self._page

    @property
    def context(self):
        return self._context

    @property
    def browser(self):
        return self._browser

    def get_console_logs(self, clear: bool = False) -> list[str]:
        """Get captured console logs."""
        logs = list(self._console_logs)
        if clear:
            self._console_logs.clear()
        return logs

    async def close(self):
        """Close browser and cleanup."""
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                finally:
                    self._browser = None
                    self._context = None
                    self._page = None
                    self._console_logs.clear()

    @property
    def is_running(self) -> bool:
        return self._browser is not None and self._page is not None


# Global singleton
_manager: Optional[BrowserManager] = None


def get_manager() -> BrowserManager:
    global _manager
    if _manager is None:
        _manager = BrowserManager()
    return _manager
