---
name: cloakbrowser-mcp
description: "Stealth browser automation via MCP — CloakBrowser with 57 C++ fingerprint patches, passes all bot detection tests."
version: 2.0.0
author: MiwooMiwoo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [MCP, Browser, Automation, Stealth, Web-Scraping]
    related_skills: [native-mcp, browser-login-automation]
---

# CloakBrowser MCP Server

Stealth browser automation via MCP protocol. Wraps CloakBrowser — a Chromium fork with 57 source-level C++ fingerprint patches that passes all 30/30 bot detection tests.

## When to Use

- Web scraping protected sites (Cloudflare, reCAPTCHA, FingerprintJS)
- Browser automation that needs to look human
- Multi-account management with persistent fingerprints
- Any task where Playwright/Puppeteer gets blocked

## Setup

### Install & Run

```bash
# Default mode (full 24-tool MCP server)
uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp

# --once mode (single-tool fetch: text + screenshot)
uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp --once
```

### Configure in Hermes

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  cloakbrowser:
    command: "uvx"
    args: ["--from", "git+https://github.com/ptbsare/cloakbrowser-mcp-server", "cloakbrowser-mcp"]
    timeout: 120
```

Restart Hermes Agent. Tools register as `mcp_cloakbrowser_cloak_*`.

### Linux Font Setup (Important!)

For sites like Kasada/Akamai that check fonts:

```bash
sudo apt install -y fonts-noto-color-emoji fonts-freefont-ttf fonts-unifont \
    fonts-ipafont-gothic fonts-wqy-zenhei fonts-tlwg-loma-otf
```

## Available Tools

All tools prefixed with `mcp_cloakbrowser_`:

| Tool | Description |
|------|-------------|
| `cloak_launch` | Launch stealth browser. Params: headless, proxy, humanize, fingerprint_seed, geoip, locale, viewport |
| `cloak_close` | Close browser |
| `cloak_navigate` | Navigate to URL, return snapshot |
| `cloak_snapshot` | Get accessibility tree with @eN ref IDs |
| `cloak_click` | Click element by ref (e.g. `@e5`) |
| `cloak_type` | Type into input by ref. Params: ref, text, submit |
| `cloak_press` | Press key (Enter, Tab, Escape, ArrowDown...) |
| `cloak_scroll` | Scroll up/down |
| `cloak_back` | Go back in history |
| `cloak_forward` | Go forward in history |
| `cloak_console` | Get console logs or evaluate JS expression |
| `cloak_get_images` | List all images (URL, alt, dimensions) |
| `cloak_screenshot` | Take PNG screenshot. Params: question, annotate |
| `cloak_wait_for` | Wait for selector or text |
| `cloak_evaluate` | Evaluate JavaScript |
| `cloak_get_content` | Get text/HTML of element or page |
| `cloak_extract_links` | Extract all links as JSON |
| `cloak_fill_form` | Fill multiple fields at once |
| `cloak_hover` | Hover over element |
| `cloak_select_option` | Select in `<select>` |
| `cloak_drag` | Drag element to element |
| `cloak_save_storage_state` | Save cookies/localStorage to JSON file |
| `cloak_load_storage_state` | Load cookies/localStorage from JSON file |
| `cloak_info` | Get URL, title, viewport info |

## Workflow

### Standard Web Interaction

1. `cloak_navigate` → loads page, returns compact snapshot with @eN refs
2. Read snapshot to identify elements
3. `cloak_click` / `cloak_type` / `cloak_press` to interact
4. `cloak_snapshot` to see updated page state
5. `cloak_close` when done

### Bypassing Bot Detection

```
1. cloak_launch(humanize=True)  ← key for anti-detection
2. cloak_navigate(url)
3. cloak_wait_for(text="Welcome")  ← wait for page to fully load
4. cloak_screenshot()  ← verify visually
5. Normal interaction...
```

### Multi-Account with Persistent Fingerprints

```
1. cloak_launch(fingerprint_seed="account-1", humanize=True)
2. ... do stuff ...
3. cloak_save_storage_state(path="account1.json")
4. cloak_close()
5. cloak_launch(fingerprint_seed="account-2", humanize=True)
6. ... different account ...
```

### Proxy + GeoIP

```
cloak_launch(
    proxy="socks5://user:pass@proxy:1080",
    geoip=True,  ← auto-detect timezone/locale from proxy IP
    humanize=True
)
```

### Auto-Load Cookies for Authenticated Scraping

Set the environment variable before launching the browser:
```bash
export CLOAKBROWSER_COOKIES_FILE=/path/to/cookies.txt
```
Cookies are auto-injected on every `cloak_launch`. Supports Netscape cookie.txt format
(exported from EditThisCookie, cookie-editor, yt-dlp, etc.).

## Pitfalls

1. **First launch is slow** — CloakBrowser downloads a ~200MB Chromium binary on first use. Subsequent launches are fast.

2. **Element refs change on every snapshot** — Always re-snapshot after page changes. Old @eN refs become stale.

3. **humanize=True is slower** — Mouse movements use Bézier curves, typing has per-character delays. Use `humanize=False` for speed when bot detection isn't a concern.

4. **headless=False recommended for tough sites** — Some aggressive detectors still flag headless. If getting blocked, try headed mode.

5. **Screenshot returns raw PNG** — The MCP server returns base64-encoded PNG. Your MCP client handles display.

6. **Console logs are buffered** — Last 500 messages. Use `clear=True` to reset buffer.

## Compared to Hermes Built-in Browser

| Feature | Hermes browser_* | CloakBrowser MCP |
|---------|-----------------|------------------|
| Stealth | ❌ Standard Playwright | ✅ 57 C++ patches |
| Bot detection | ❌ Fails most tests | ✅ Passes 30/30 |
| Humanize | ❌ No | ✅ Bézier mouse, typing |
| Proxy | ❌ No | ✅ HTTP/SOCKS5 |
| Fingerprint | ❌ Random | ✅ Deterministic seeds |
| Session save | ❌ No | ✅ Cookies + localStorage |
| Speed | ✅ Fast | ⚡ Slightly slower (stealth overhead) |

Use CloakBrowser MCP when you need stealth. Use built-in browser tools for simple, non-protected sites.

## Links

- GitHub: https://github.com/MiwooMiwoo/cloakbrowser-mcp
- CloakBrowser: https://github.com/CloakHQ/CloakBrowser
- MCP Protocol: https://modelcontextprotocol.io/
