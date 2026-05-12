# CloakBrowser MCP Server

[English](README.md) | [中文](README_CN.md)

> Stealth browser automation via [Model Context Protocol](https://modelcontextprotocol.io/), powered by [CloakBrowser](https://github.com/CloakHQ/CloakBrowser).

A drop-in MCP server that wraps CloakBrowser's stealth Chromium with **57 source-level C++ fingerprint patches** — not JS injection. Passes all 30/30 bot detection tests (reCAPTCHA v3 score: 0.9, Cloudflare Turnstile: PASS, FingerprintJS: PASS).

All tools use the `cloak_` prefix to avoid conflicts with Hermes Agent's built-in `browser_*` tools.

## Features

- **22 cloak tools** — navigate, click, type, screenshot, console, evaluate JS, form filling, drag & drop, and more
- **Stealth by default** — `navigator.webdriver = false`, real Chrome TLS fingerprint, no CDP detection
- **Human-like behavior** — `humanize=True` enables Bézier mouse curves, per-character keyboard timing
- **Proxy support** — HTTP & SOCKS5 with GeoIP auto-detection
- **Session persistence** — save/load cookies and localStorage
- **Compatible with any MCP client** — Hermes Agent, Claude Desktop, Cursor, etc.
- **No naming conflicts** — `cloak_*` prefix won't collide with Hermes built-in `browser_*` tools

## Quick Start

### Install

```bash
pip install mcp-cloakbrowser
```

### Run

```bash
# As a stdio MCP server
mcp-cloakbrowser

# Or directly
python -m cloakbrowser_mcp.server
```

### Use with Hermes Agent

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  cloakbrowser:
    command: "python"
    args: ["-m", "cloakbrowser_mcp.server"]
    timeout: 120
```

Restart Hermes Agent. Tools will be registered as `mcp_cloakbrowser_cloak_*`.

### Use with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cloakbrowser": {
      "command": "mcp-cloakbrowser"
    }
  }
}
```

## Available Tools

All tools use the `cloak_` prefix (registered as `mcp_cloakbrowser_cloak_*` in Hermes):

| Tool | Description |
|------|-------------|
| `cloak_launch` | Launch a stealth CloakBrowser instance |
| `cloak_close` | Close the browser and clean up |
| `cloak_navigate` | Navigate to a URL, return compact snapshot |
| `cloak_snapshot` | Get accessibility tree with ref IDs |
| `cloak_click` | Click element by ref (e.g. `@e5`) |
| `cloak_type` | Type text into input field by ref |
| `cloak_press` | Press keyboard key (Enter, Tab, Escape...) |
| `cloak_scroll` | Scroll page up/down |
| `cloak_back` | Navigate back in history |
| `cloak_forward` | Navigate forward in history |
| `cloak_console` | Get console logs or evaluate JS |
| `cloak_get_images` | List all images with URLs and alt text |
| `cloak_screenshot` | Take PNG screenshot |
| `cloak_wait_for` | Wait for element or text to appear |
| `cloak_evaluate` | Evaluate JavaScript expression |
| `cloak_get_content` | Get text/HTML of page or element |
| `cloak_extract_links` | Extract all links as JSON |
| `cloak_fill_form` | Fill multiple form fields at once |
| `cloak_hover` | Hover over element by ref |
| `cloak_select_option` | Select options in `<select>` elements |
| `cloak_drag` | Drag element to another element |
| `cloak_save_storage_state` | Save cookies/localStorage to file |
| `cloak_load_storage_state` | Load cookies/localStorage from file |
| `cloak_info` | Get current page URL, title, viewport |

## Tool Usage Examples

### Navigate and Interact

```python
# Launch browser
await call_tool("cloak_launch", {"headless": True, "humanize": True})

# Navigate to a page
await call_tool("cloak_navigate", {"url": "https://example.com"})

# Get snapshot to see interactive elements
snapshot = await call_tool("cloak_snapshot", {})
# Shows: [@e1] <a>Link text, [@e2] <input>[type: text]...

# Click a link
await call_tool("cloak_click", {"ref": "@e1"})

# Type into search box
await call_tool("cloak_type", {"ref": "@e2", "text": "hello world", "submit": True})

# Take screenshot
await call_tool("cloak_screenshot", {})
```

### Fill a Login Form

```python
await call_tool("cloak_fill_form", {
    "fields": [
        {"ref": "@e1", "value": "username"},
        {"ref": "@e2", "value": "password123"},
    ],
    "submit_ref": "@e3",
})
```

### Advanced: Custom Fingerprint & Proxy

```python
await call_tool("cloak_launch", {
    "headless": True,
    "humanize": True,
    "proxy": "socks5://user:pass@proxy:1080",
    "fingerprint_seed": "my-unique-seed-123",
    "geoip": True,
    "locale": "zh-CN",
})
```

### Save/Restore Session

```python
# Save session after login
await call_tool("cloak_save_storage_state", {"path": "session.json"})

# Later: restore session
await call_tool("cloak_load_storage_state", {"path": "session.json"})
```

## Why `cloak_*` Prefix?

Hermes Agent has built-in `browser_*` tools (browser_navigate, browser_click, etc.) that use its own Playwright instance. Using the same names would cause conflicts. The `cloak_` prefix makes it clear these tools use CloakBrowser's stealth Chromium, and allows you to use both in the same session:

- `browser_navigate` → Hermes built-in Playwright (fast, no stealth)
- `cloak_navigate` → CloakBrowser stealth Chromium (passes bot detection)

## Architecture

```
MCP Client (Hermes/Claude/etc.)
    │ stdio (JSON-RPC)
    ▼
mcp-cloakbrowser server
    │
    ▼
CloakBrowser (Playwright-compatible API)
    │
    ▼
Stealth Chromium (57 C++ patches)
```

The server maintains a single browser instance (singleton pattern). All tools operate on the current page. The browser is auto-launched on first tool call if not explicitly launched.

## Development

```bash
git clone https://github.com/MiwooMiwoo/cloakbrowser-mcp.git
cd cloakbrowser-mcp
pip install -e ".[dev]"
```

## License

MIT
