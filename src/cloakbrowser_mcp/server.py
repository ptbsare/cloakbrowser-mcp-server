"""CloakBrowser MCP Server - Main entry point.

Stealth browser automation via MCP protocol, powered by CloakBrowser.

Two modes:
  Default: full MCP server with all interactive tools (--caps controls subsets).
  --once:  single-tool "fetch" mode for automated scraping. One tool, one URL,
           returns text + screenshot, then exits. All stealth defaults enabled.
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    ImageContent,
    Tool,
)

from . import tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("cloakbrowser-mcp")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_once_mode: bool = False
_caps: set[str] = set()


def _text(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _image(data: str, format: str = "png") -> list[ImageContent]:
    return [ImageContent(type="image", data=data, mimeType=f"image/{format}")]


def _build_full_server() -> Server:
    """Build the normal multi-tool MCP server."""
    server = Server("cloakbrowser-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tool_list: list[Tool] = [
            Tool(
                name="cloak_launch",
                description="Launch a stealth CloakBrowser instance. Stealth features ON by default (humanize, geoip).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "headless": {"type": "boolean", "default": True, "description": "Run in headless mode. Default True."},
                        "proxy": {"type": "string", "description": "Proxy URL (http/socks5)."},
                        "humanize": {"type": "boolean", "default": True, "description": "Human-like mouse/keyboard. Default True."},
                        "user_agent": {"type": "string", "description": "Custom User-Agent string."},
                        "viewport_width": {"type": "integer", "default": 1280, "description": "Viewport width in pixels."},
                        "viewport_height": {"type": "integer", "default": 720, "description": "Viewport height in pixels."},
                        "locale": {"type": "string", "description": "Browser locale (e.g. 'en-US', 'zh-CN')."},
                        "fingerprint_seed": {"type": "string", "description": "Deterministic fingerprint seed."},
                        "geoip": {"type": "boolean", "default": True, "description": "Auto-detect timezone/locale from proxy IP. Default True."},
                    },
                },
            ),
            Tool(name="cloak_close", description="Close the browser and clean up resources.", inputSchema={"type": "object", "properties": {}}),
            Tool(
                name="cloak_navigate",
                description="Navigate to a URL and return full page content + interactive elements.",
                inputSchema={"type": "object", "properties": {"url": {"type": "string", "description": "The URL to navigate to."}}, "required": ["url"]},
            ),
            Tool(
                name="cloak_snapshot",
                description="Get page content and interactive elements with ref IDs.",
                inputSchema={"type": "object", "properties": {"full": {"type": "boolean", "default": False, "description": "Include full page content."}}},
            ),
            Tool(
                name="cloak_click",
                description="Click element by ref ID (e.g. '@e5').",
                inputSchema={"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"]},
            ),
            Tool(
                name="cloak_type",
                description="Type text into input by ref ID.",
                inputSchema={"type": "object", "properties": {"ref": {"type": "string"}, "text": {"type": "string"}, "submit": {"type": "boolean", "default": False}}, "required": ["ref", "text"]},
            ),
            Tool(
                name="cloak_press",
                description="Press a keyboard key.",
                inputSchema={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
            ),
            Tool(
                name="cloak_scroll",
                description="Scroll the page.",
                inputSchema={"type": "object", "properties": {"direction": {"type": "string", "enum": ["up", "down"], "default": "down"}}},
            ),
            Tool(name="cloak_back", description="Navigate back.", inputSchema={"type": "object", "properties": {}}),
            Tool(name="cloak_forward", description="Navigate forward.", inputSchema={"type": "object", "properties": {}}),
            Tool(
                name="cloak_console",
                description="Get console logs or evaluate JS.",
                inputSchema={"type": "object", "properties": {"clear": {"type": "boolean", "default": False}, "expression": {"type": "string"}}},
            ),
            Tool(name="cloak_get_images", description="List all images on the page.", inputSchema={"type": "object", "properties": {}}),
            Tool(
                name="cloak_screenshot",
                description="Take a PNG screenshot.",
                inputSchema={"type": "object", "properties": {"question": {"type": "string"}, "annotate": {"type": "boolean", "default": False}}},
            ),
            Tool(
                name="cloak_wait_for",
                description="Wait for element or text.",
                inputSchema={"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}, "timeout": {"type": "integer", "default": 10000}}},
            ),
            Tool(
                name="cloak_evaluate",
                description="Evaluate JavaScript.",
                inputSchema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
            ),
            Tool(
                name="cloak_get_content",
                description="Get clean text or HTML of page/element.",
                inputSchema={"type": "object", "properties": {"selector": {"type": "string", "default": "body"}, "text_only": {"type": "boolean", "default": True}, "max_length": {"type": "integer", "default": 10000}}},
            ),
            Tool(name="cloak_extract_links", description="Extract all links as JSON.", inputSchema={"type": "object", "properties": {}}),
            Tool(
                name="cloak_fill_form",
                description="Fill multiple form fields.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "fields": {"type": "array", "items": {"type": "object", "properties": {"ref": {"type": "string"}, "value": {"type": "string"}}, "required": ["ref", "value"]}},
                        "submit_ref": {"type": "string"},
                    },
                    "required": ["fields"],
                },
            ),
            Tool(name="cloak_hover", description="Hover over element by ref.", inputSchema={"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"]),
            Tool(name="cloak_select_option", description="Select dropdown option.", inputSchema={"type": "object", "properties": {"ref": {"type": "string"}, "values": {"type": "array", "items": {"type": "string"}}}, "required": ["ref", "values"]),
            Tool(name="cloak_drag", description="Drag element to element.", inputSchema={"type": "object", "properties": {"ref_from": {"type": "string"}, "ref_to": {"type": "string"}}, "required": ["ref_from", "ref_to"]),
            Tool(name="cloak_save_storage_state", description="Save cookies/localStorage to JSON.", inputSchema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]),
            Tool(name="cloak_load_storage_state", description="Load cookies/localStorage from JSON.", inputSchema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]),
            Tool(name="cloak_info", description="Get current page URL, title, viewport.", inputSchema={"type": "object", "properties": {}}),
        ]
        return tool_list

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
        try:
            if name == "cloak_launch":
                return _text(await tools.tool_launch(**arguments))
            elif name == "cloak_close":
                return _text(await tools.tool_close())
            elif name == "cloak_navigate":
                return _text(await tools.tool_navigate(**arguments))
            elif name == "cloak_snapshot":
                return _text(await tools.tool_snapshot(**arguments))
            elif name == "cloak_click":
                return _text(await tools.tool_click(**arguments))
            elif name == "cloak_type":
                return _text(await tools.tool_type(**arguments))
            elif name == "cloak_press":
                return _text(await tools.tool_press(**arguments))
            elif name == "cloak_scroll":
                return _text(await tools.tool_scroll(**arguments))
            elif name == "cloak_back":
                return _text(await tools.tool_back())
            elif name == "cloak_forward":
                return _text(await tools.tool_forward())
            elif name == "cloak_console":
                return _text(await tools.tool_console(**arguments))
            elif name == "cloak_get_images":
                return _text(await tools.tool_get_images())
            elif name == "cloak_screenshot":
                r = await tools.tool_screenshot(**arguments)
                return _text(r["error"]) if "error" in r else [ImageContent(type="image", data=r["data"], mimeType="image/png")]
            elif name == "cloak_wait_for":
                return _text(await tools.tool_wait_for(**arguments))
            elif name == "cloak_evaluate":
                return _text(await tools.tool_evaluate(**arguments))
            elif name == "cloak_get_content":
                return _text(await tools.tool_get_content(**arguments))
            elif name == "cloak_extract_links":
                return _text(await tools.tool_extract_links())
            elif name == "cloak_fill_form":
                return _text(await tools.tool_fill_form(**arguments))
            elif name == "cloak_hover":
                return _text(await tools.tool_hover(**arguments))
            elif name == "cloak_select_option":
                return _text(await tools.tool_select_option(**arguments))
            elif name == "cloak_drag":
                return _text(await tools.tool_drag(**arguments))
            elif name == "cloak_save_storage_state":
                return _text(await tools.tool_save_storage_state(**arguments))
            elif name == "cloak_load_storage_state":
                return _text(await tools.tool_load_storage_state(**arguments))
            elif name == "cloak_info":
                return _text(await tools.tool_info())
            else:
                return _text(f"Unknown tool: {name}")
        except Exception as e:
            logger.exception(f"Error in tool {name}")
            return _text(f"Error: {e}")

    return server


def _build_once_server() -> Server:
    """Build the single-tool --once fetch server."""
    server = Server("cloakbrowser-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="cloak_fetch",
                description=(
                    "Fetch a web page and return its text content + screenshot. "
                    "One-shot: launches browser with all stealth defaults "
                    "(headless, humanize, geoip), loads cookies from "
                    "CLOAKBROWSER_COOKIES_FILE env var, navigates to URL, "
                    "waits for page load, extracts clean text, takes screenshot, "
                    "closes browser. Returns text, screenshot (image), url, title."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to fetch."},
                        "max_length": {"type": "integer", "default": 50000, "description": "Max text length in characters."},
                    },
                    "required": ["url"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
        if name != "cloak_fetch":
            return _text(f"Unknown tool: {name}")
        try:
            result = await tools.tool_fetch(**arguments)
            if "error" in result:
                return _text(f"Error: {result['error']}")
            parts: list[TextContent | ImageContent] = [
                TextContent(type="text", text=f"URL: {result['url']}\nTitle: {result['title']}\n\n{result['text']}"),
                ImageContent(type="image", data=result["screenshot"], mimeType="image/png"),
            ]
            return parts
        except Exception as e:
            logger.exception("Error in cloak_fetch")
            return _text(f"Error: {e}")

    return server


async def main():
    """Run the MCP server."""
    global _once_mode
    if _once_mode:
        logger.info("Starting CloakBrowser MCP Server (--once mode)...")
    else:
        logger.info("Starting CloakBrowser MCP Server...")
    server = _build_once_server() if _once_mode else _build_full_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run():
    """Entry point for CLI."""
    global _once_mode
    parser = argparse.ArgumentParser(description="CloakBrowser MCP Server")
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Single-tool fetch mode. Only exposes cloak_fetch(url) which returns text + screenshot.",
    )
    args = parser.parse_args()
    _once_mode = args.once
    asyncio.run(main())


if __name__ == "__main__":
    run()
