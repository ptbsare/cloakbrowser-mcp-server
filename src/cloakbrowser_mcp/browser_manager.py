"""Browser lifecycle manager for CloakBrowser MCP Server."""

import asyncio
import base64
import io
import json
import logging
import os
from pathlib import Path
from typing import Optional

# Environment variable for auto-loading cookies on browser launch
COOKIES_FILE_ENV = "CLOAKBROWSER_COOKIES_FILE"

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

            # Auto-load cookies from file if CLOAKBROWSER_COOKIES_FILE is set
            await self._auto_load_cookies_from_env()

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

    async def _auto_load_cookies_from_env(self) -> None:
        """If CLOAKBROWSER_COOKIES_FILE is set, parse and inject cookies
        in Netscape cookie.txt format (the standard export format used by
        browser extensions like EditThisCookie, cookie-editor, etc.)."""
        cookie_file = os.environ.get(COOKIES_FILE_ENV)
        if not cookie_file:
            return

        path = Path(cookie_file)
        if not path.exists():
            logger.warning(
                "%s is set to '%s' but the file does not exist - skipping.",
                COOKIES_FILE_ENV, cookie_file,
            )
            return

        cookies = self._parse_netscape_cookie_file(path)
        if cookies:
            try:
                await self._context.add_cookies(cookies)
                logger.info(
                    "Auto-loaded %d cookie(s) from %s (via %s)",
                    len(cookies), cookie_file, COOKIES_FILE_ENV,
                )
            except Exception as exc:
                logger.error("Failed to inject cookies from %s: %s", cookie_file, exc)
        else:
            logger.warning("No valid cookies found in %s", cookie_file)

    @staticmethod
    def _parse_netscape_cookie_file(path: Path) -> list[dict]:
        """Parse a Netscape-format cookie.txt file.

        Each line has tab-separated fields:
            domain  httpOnly  path  secure  expires  name  value

        Lines starting with '#' are comments and are skipped.
        """
        cookies: list[dict] = []
        with open(path, "r", encoding="utf-8") as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 7:
                    logger.debug(
                        "Skipping line %d in %s (expected 7 tab-separated fields, got %d)",
                        lineno, path, len(parts),
                    )
                    continue
                domain, http_only_str, cookie_path, secure_str, expires_str, name, value = (
                    parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]
                )
                # Convert expires: "0" or empty means session cookie (use -1)
                try:
                    expires = int(expires_str)
                except ValueError:
                    expires = -1
                if expires == 0:
                    expires = -1

                cookies.append({
                    "domain": domain,
                    "path": cookie_path,
                    "secure": secure_str.upper() == "TRUE",
                    "httpOnly": http_only_str.upper() == "TRUE",
                    "expires": expires,
                    "name": name,
                    "value": value,
                })
        return cookies

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
