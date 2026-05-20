# CloakBrowser MCP Server

[English](README.md) | [中文](README_CN.md)

> Stealth browser automation via [Model Context Protocol](https://modelcontextprotocol.io/), powered by [CloakBrowser](https://github.com/CloakHQ/CloakBrowser).

A drop-in MCP server wrapping CloakBrowser's stealth Chromium with **57 source-level C++ fingerprint patches** — not JS injection. Passes all 30/30 bot detection tests (reCAPTCHA v3 score: 0.9, Cloudflare Turnstile: PASS, FingerprintJS: PASS).

Two modes:
- **Default mode** — 24 interactive tools for full browser automation (navigate, click, type, screenshot, etc.)
- **`--once` mode** — single `cloak_fetch(url)` tool for automated scraping, returns text + screenshot, zero config

## Quick Start

### Install & Run

No install needed. Run directly via [uvx](https://docs.astral.sh/uv/guides/tools/) from the Git repo:

```bash
# Default mode (full 24-tool MCP server)
uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp

# --once mode (single-tool fetch: text + screenshot)
uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp --once
```

CloakBrowser's patched Chromium (~200MB) auto-downloads on first run. Subsequent launches are fast.

### Use with Claude Desktop / Cursor

Add to `claude_desktop_mcp.json` or `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "cloakbrowser": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/ptbsare/cloakbrowser-mcp-server", "cloakbrowser-mcp"]
    }
  }
}
```

For `--once` mode, append `"--once"` to the args list.

### Use with Hermes Agent

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  cloakbrowser:
    command: "uvx"
    args: ["--from", "git+https://github.com/ptbsare/cloakbrowser-mcp-server", "cloakbrowser-mcp"]
    timeout: 120
```

## --once Mode (Automated Scraping)

Designed for machine scraping. One tool, one URL, returns everything:

```bash
# Optional: auto-load login cookies and/or persistent profile
export CLOAKBROWSER_COOKIES_FILE=/path/to/cookies.txt
export CLOAKBROWSER_USER_DATA_DIR=/path/to/browser-profile

uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp --once
```

The AI agent only needs to call:

```
cloak_fetch(url="https://example.com")
```

Returns:
- **text** — clean visible page content (CSS/JS stripped, whitespace collapsed)
- **screenshot** — full-page PNG image
- **url** — final URL after redirects
- **title** — page title

All anti-detection defaults are auto-enabled: `headless=True`, `humanize=True`, `geoip=True`. No parameters to think about.

## Default Mode (Full Automation)

24 interactive tools for complete browser control. All tools use the `cloak_` prefix to avoid conflicts with Hermes Agent's built-in `browser_*` tools.

### Stealth Defaults

`cloak_launch` enables all anti-detection by default:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `headless` | `True` | Headless mode (set `False` for headed) |
| `humanize` | `True` | Bézier mouse curves, per-character typing |
| `geoip` | `True` | Auto-detect timezone/locale from proxy IP |

Explicitly pass `headless=False`, `humanize=False`, or `geoip=False` to disable.

### Available Tools

| Tool | Description |
|------|-------------|
| `cloak_launch` | Launch stealth browser (stealth ON by default) |
| `cloak_close` | Close browser and release resources |
| `cloak_navigate` | Navigate to URL, return full page content + interactive elements |
| `cloak_snapshot` | Get page content and interactive elements with `[@eN]` ref IDs |
| `cloak_click` | Click element by ref (e.g. `@e5`) |
| `cloak_type` | Type text into input by ref |
| `cloak_press` | Press keyboard key (Enter, Tab, Escape...) |
| `cloak_scroll` | Scroll page up/down |
| `cloak_back` | Navigate back in history |
| `cloak_forward` | Navigate forward in history |
| `cloak_console` | Get console logs or evaluate JS |
| `cloak_get_images` | List all images with URLs and alt text |
| `cloak_screenshot` | Take PNG screenshot |
| `cloak_wait_for` | Wait for element or text to appear |
| `cloak_evaluate` | Evaluate JavaScript expression |
| `cloak_get_content` | Get clean text or HTML of page/element |
| `cloak_extract_links` | Extract all links as JSON |
| `cloak_fill_form` | Fill multiple form fields at once |
| `cloak_hover` | Hover over element by ref |
| `cloak_select_option` | Select options in `<select>` elements |
| `cloak_drag` | Drag element to another element |
| `cloak_save_storage_state` | Save cookies/localStorage to JSON file |
| `cloak_load_storage_state` | Load cookies/localStorage from JSON file |
| `cloak_info` | Get current page URL, title, viewport |

### Tool Usage Examples

#### Navigate and Interact

```python
# Launch browser (stealth defaults auto-enabled)
await call_tool("cloak_launch", {})

# Navigate to a page — returns full content + interactive elements
result = await call_tool("cloak_navigate", {"url": "https://example.com"})

# Get snapshot with ref IDs for interaction
snapshot = await call_tool("cloak_snapshot", {})
# Shows: [@e1] <a>Link text, [@e2] <input>[type: text]...

# Click a link
await call_tool("cloak_click", {"ref": "@e1"})

# Type into search box and submit
await call_tool("cloak_type", {"ref": "@e2", "text": "hello world", "submit": True})

# Take screenshot
await call_tool("cloak_screenshot", {})
```

#### Fill a Login Form

```python
await call_tool("cloak_fill_form", {
    "fields": [
        {"ref": "@e1", "value": "username"},
        {"ref": "@e2", "value": "password123"},
    ],
    "submit_ref": "@e3",
})
```

#### Custom Fingerprint & Proxy

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

#### Save/Restore Session

```python
# Save session after login
await call_tool("cloak_save_storage_state", {"path": "session.json"})

# Later: restore session
await call_tool("cloak_load_storage_state", {"path": "session.json"})
```

## Cookie Management

### Auto-Load Cookies (all modes)

Set the environment variable and cookies are auto-loaded on every browser launch:

```bash
export CLOAKBROWSER_COOKIES_FILE=/path/to/cookies.txt
```

Supports standard Netscape cookie.txt format (tab-separated), exportable from:
- Chrome extensions: EditThisCookie, cookie-editor
- Firefox extensions: cookies.txt
- CLI tools: `yt-dlp --cookies cookies.txt`, etc.

File format:
```
.example.com	TRUE	/	TRUE	1735689600	session_id	abc123xyz
.example.com	TRUE	/	FALSE	0	user_pref	dark_mode
```

Fully transparent to the AI agent — no extra tool calls needed.

### Persistent Browser Profile

Set `CLOAKBROWSER_USER_DATA_DIR` to a directory path and the browser will
persist its state (cookies, localStorage, login sessions, Cloudflare
clearance) across restarts. Login once, stay logged in forever:

```bash
export CLOAKBROWSER_USER_DATA_DIR=/path/to/browser-profile
```

This uses Playwright's `user_data_dir` mechanism under the hood. The
directory is created automatically if it doesn't exist.

**Recommended workflow:**
1. Set `CLOAKBROWSER_USER_DATA_DIR` and `CLOAKBROWSER_COOKIES_FILE`
2. Launch the browser and log in manually (or via `cloak_fill_form`)
3. On subsequent launches, login state is preserved automatically
4. No need to re-import cookies each time

Combine with cookie auto-load for the best of both worlds:
```bash
export CLOAKBROWSER_USER_DATA_DIR=/path/to/browser-profile
export CLOAKBROWSER_COOKIES_FILE=/path/to/cookies.txt
uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp
```

## Why `cloak_*` Prefix?

Hermes Agent has built-in `browser_*` tools (browser_navigate, browser_click, etc.) that use its own Playwright instance. The `cloak_` prefix avoids conflicts and allows both to coexist:

- `browser_navigate` → Hermes built-in Playwright (fast, no stealth)
- `cloak_navigate` → CloakBrowser stealth Chromium (passes bot detection)

## Architecture

```
MCP Client (Hermes / Claude / Cursor / etc.)
    │ stdio (JSON-RPC)
    ▼
cloakbrowser-mcp server
    │
    ├── Default mode: 24 interactive tools
    └── --once mode: 1 fetch tool (cloak_fetch)
    │
    ▼
CloakBrowser (Playwright-compatible API)
    │
    ▼
Stealth Chromium (57 C++ source-level patches)
```

The server maintains a single browser instance (singleton pattern). In default mode the browser persists across tool calls. In `--once` mode the browser auto-closes after each fetch.

## Development

```bash
git clone https://github.com/ptbsare/cloakbrowser-mcp-server
cd cloakbrowser-mcp-server
pip install -e ".[dev]"
```

## License

MIT
