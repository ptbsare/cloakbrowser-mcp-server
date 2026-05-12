---
name: cloakbrowser-mcp
description: "Stealth browser automation via MCP — CloakBrowser with 57 C++ fingerprint patches, passes all bot detection tests."
version: 1.0.0
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

### Install

```bash
pip install cloakbrowser-mcp
```

### Configure in Hermes

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  cloakbrowser:
    command: "python"
    args: ["-m", "cloakbrowser_mcp.server"]
    timeout: 120
```

Restart Hermes Agent. Tools register as `mcp_cloakbrowser_browser_*`.

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
| `browser_launch` | Launch stealth browser. Params: headless, proxy, humanize, fingerprint_seed, geoip, locale, viewport |
| `browser_close` | Close browser |
| `browser_navigate` | Navigate to URL, return snapshot |
| `browser_snapshot` | Get accessibility tree with @eN ref IDs |
| `browser_click` | Click element by ref (e.g. `@e5`) |
| `browser_type` | Type into input by ref. Params: ref, text, submit |
| `browser_press` | Press key (Enter, Tab, Escape, ArrowDown...) |
| `browser_scroll` | Scroll up/down |
| `browser_back` | Go back in history |
| `browser_forward` | Go forward in history |
| `browser_console` | Get console logs or evaluate JS expression |
| `browser_get_images` | List all images (URL, alt, dimensions) |
| `browser_screenshot` | Take PNG screenshot. Params: question, annotate |
| `browser_wait_for` | Wait for selector or text |
| `browser_evaluate` | Evaluate JavaScript |
| `browser_get_content` | Get text/HTML of element or page |
| `browser_extract_links` | Extract all links as JSON |
| `browser_fill_form` | Fill multiple fields at once |
| `browser_hover` | Hover over element |
| `browser_select_option` | Select in `<select>` |
| `browser_drag` | Drag element to element |
| `browser_save_storage_state` | Save cookies/localStorage |
| `browser_load_storage_state` | Load cookies/localStorage |
| `browser_info` | Get URL, title, viewport info |

## Workflow

### Standard Web Interaction

1. `browser_navigate` → loads page, returns compact snapshot with @eN refs
2. Read snapshot to identify elements
3. `browser_click` / `browser_type` / `browser_press` to interact
4. `browser_snapshot` to see updated page state
5. `browser_close` when done

### Bypassing Bot Detection

```
1. browser_launch(humanize=True)  ← key for anti-detection
2. browser_navigate(url)
3. browser_wait_for(text="Welcome")  ← wait for page to fully load
4. browser_screenshot()  ← verify visually
5. Normal interaction...
```

### Multi-Account with Persistent Fingerprints

```
1. browser_launch(fingerprint_seed="account-1", humanize=True)
2. ... do stuff ...
3. browser_save_storage_state(path="account1.json")
4. browser_close()
5. browser_launch(fingerprint_seed="account-2", humanize=True)
6. ... different account ...
```

### Proxy + GeoIP

```
browser_launch(
    proxy="socks5://user:pass@proxy:1080",
    geoip=True,  ← auto-detect timezone/locale from proxy IP
    humanize=True
)
```

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
