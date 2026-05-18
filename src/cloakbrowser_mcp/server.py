"""CloakBrowser MCP Server - Main entry point.

Stealth browser automation via MCP protocol, powered by CloakBrowser.
Provides all cloak tools: navigate, click, type, screenshot, console, etc.
"""

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

app = Server("cloakbrowser-mcp")


def _text(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _image(data: str, format: str = "png") -> list[ImageContent]:
    return [ImageContent(type="image", data=data, mimeType=f"image/{format}")]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available cloak tools."""
    return [
        Tool(
            name="cloak_launch",
            description="Launch a stealth CloakBrowser instance. Stealth features ON by default (headed, humanize, geoip). Pass headless=True for server use.",
            inputSchema={
                "type": "object",
                "properties": {
                    "headless": {"type": "boolean", "default": False, "description": "Run headless. Default False (headed) for best stealth."},
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
        Tool(
            name="cloak_close",
            description="Close the browser and clean up resources.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cloak_navigate",
            description="Navigate to a URL and return a compact snapshot of the page.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to."},
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="cloak_snapshot",
            description="Get a text-based snapshot of the current page's accessibility tree with ref IDs for interactive elements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "full": {"type": "boolean", "default": False, "description": "If true, return complete page content."},
                },
            },
        ),
        Tool(
            name="cloak_click",
            description="Click on an element identified by its ref ID from the snapshot (e.g. '@e5').",
            inputSchema={
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "The element reference (e.g. '@e5')."},
                },
                "required": ["ref"],
            },
        ),
        Tool(
            name="cloak_type",
            description="Type text into an input field identified by its ref ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "The element reference (e.g. '@e3')."},
                    "text": {"type": "string", "description": "The text to type."},
                    "submit": {"type": "boolean", "default": False, "description": "Press Enter after typing."},
                },
                "required": ["ref", "text"],
            },
        ),
        Tool(
            name="cloak_press",
            description="Press a keyboard key (Enter, Tab, Escape, ArrowDown, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to press."},
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="cloak_scroll",
            description="Scroll the page in a direction.",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"], "default": "down", "description": "Direction to scroll."},
                },
            },
        ),
        Tool(
            name="cloak_back",
            description="Navigate back in browser history.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cloak_forward",
            description="Navigate forward in browser history.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cloak_console",
            description="Get browser console output or evaluate JavaScript expression.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clear": {"type": "boolean", "default": False, "description": "Clear console log buffer after reading."},
                    "expression": {"type": "string", "description": "JavaScript expression to evaluate."},
                },
            },
        ),
        Tool(
            name="cloak_get_images",
            description="Get a list of all images on the current page with URLs and alt text.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cloak_screenshot",
            description="Take a screenshot of the current page. Returns a PNG image.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "What you want to know about the page visually."},
                    "annotate": {"type": "boolean", "default": False, "description": "Overlay numbered labels on interactive elements."},
                },
            },
        ),
        Tool(
            name="cloak_wait_for",
            description="Wait for an element or text to appear on the page.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector to wait for."},
                    "text": {"type": "string", "description": "Text content to wait for."},
                    "timeout": {"type": "integer", "default": 10000, "description": "Timeout in milliseconds."},
                },
            },
        ),
        Tool(
            name="cloak_evaluate",
            description="Evaluate JavaScript expression in the page context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "JavaScript expression to evaluate."},
                },
                "required": ["expression"],
            },
        ),
        Tool(
            name="cloak_get_content",
            description="Get text or HTML content of an element or the entire page.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "default": "body", "description": "CSS selector."},
                    "text_only": {"type": "boolean", "default": True, "description": "Return text only (vs innerHTML)."},
                    "max_length": {"type": "integer", "default": 10000, "description": "Max content length."},
                },
            },
        ),
        Tool(
            name="cloak_extract_links",
            description="Extract all links from the current page as JSON.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cloak_fill_form",
            description="Fill multiple form fields at once.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ref": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["ref", "value"],
                        },
                        "description": "List of {ref, value} objects.",
                    },
                    "submit_ref": {"type": "string", "description": "Optional ref of submit button."},
                },
                "required": ["fields"],
            },
        ),
        Tool(
            name="cloak_hover",
            description="Hover over an element identified by its ref ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "The element reference."},
                },
                "required": ["ref"],
            },
        ),
        Tool(
            name="cloak_select_option",
            description="Select option(s) in a <select> element.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "The <select> element reference."},
                    "values": {"type": "array", "items": {"type": "string"}, "description": "Option values to select."},
                },
                "required": ["ref", "values"],
            },
        ),
        Tool(
            name="cloak_drag",
            description="Drag an element from one position to another.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ref_from": {"type": "string", "description": "Source element reference."},
                    "ref_to": {"type": "string", "description": "Target element reference."},
                },
                "required": ["ref_from", "ref_to"],
            },
        ),
        Tool(
            name="cloak_save_storage_state",
            description="Save browser storage state (cookies, localStorage) to a JSON file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to save."},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="cloak_load_storage_state",
            description="Load browser storage state from a JSON file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to load."},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="cloak_info",
            description="Get information about the current browser session (URL, title, viewport).",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
    """Route tool calls to implementations."""
    try:
        if name == "cloak_launch":
            result = await tools.tool_launch(**arguments)
            return _text(result)
        elif name == "cloak_close":
            result = await tools.tool_close()
            return _text(result)
        elif name == "cloak_navigate":
            result = await tools.tool_navigate(**arguments)
            return _text(result)
        elif name == "cloak_snapshot":
            result = await tools.tool_snapshot(**arguments)
            return _text(result)
        elif name == "cloak_click":
            result = await tools.tool_click(**arguments)
            return _text(result)
        elif name == "cloak_type":
            result = await tools.tool_type(**arguments)
            return _text(result)
        elif name == "cloak_press":
            result = await tools.tool_press(**arguments)
            return _text(result)
        elif name == "cloak_scroll":
            result = await tools.tool_scroll(**arguments)
            return _text(result)
        elif name == "cloak_back":
            result = await tools.tool_back()
            return _text(result)
        elif name == "cloak_forward":
            result = await tools.tool_forward()
            return _text(result)
        elif name == "cloak_console":
            result = await tools.tool_console(**arguments)
            return _text(result)
        elif name == "cloak_get_images":
            result = await tools.tool_get_images()
            return _text(result)
        elif name == "cloak_screenshot":
            result = await tools.tool_screenshot(**arguments)
            if "error" in result:
                return _text(result["error"])
            return [ImageContent(type="image", data=result["data"], mimeType="image/png")]
        elif name == "cloak_wait_for":
            result = await tools.tool_wait_for(**arguments)
            return _text(result)
        elif name == "cloak_evaluate":
            result = await tools.tool_evaluate(**arguments)
            return _text(result)
        elif name == "cloak_get_content":
            result = await tools.tool_get_content(**arguments)
            return _text(result)
        elif name == "cloak_extract_links":
            result = await tools.tool_extract_links()
            return _text(result)
        elif name == "cloak_fill_form":
            result = await tools.tool_fill_form(**arguments)
            return _text(result)
        elif name == "cloak_hover":
            result = await tools.tool_hover(**arguments)
            return _text(result)
        elif name == "cloak_select_option":
            result = await tools.tool_select_option(**arguments)
            return _text(result)
        elif name == "cloak_drag":
            result = await tools.tool_drag(**arguments)
            return _text(result)
        elif name == "cloak_save_storage_state":
            result = await tools.tool_save_storage_state(**arguments)
            return _text(result)
        elif name == "cloak_load_storage_state":
            result = await tools.tool_load_storage_state(**arguments)
            return _text(result)
        elif name == "cloak_info":
            result = await tools.tool_info()
            return _text(result)
        else:
            return _text(f"Unknown tool: {name}")
    except Exception as e:
        logger.exception(f"Error in tool {name}")
        return _text(f"Error: {e}")


async def main():
    """Run the MCP server."""
    logger.info("Starting CloakBrowser MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run():
    """Entry point for CLI."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
