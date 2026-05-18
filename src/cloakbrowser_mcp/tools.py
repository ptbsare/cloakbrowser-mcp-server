"""MCP tool implementations for CloakBrowser."""

import asyncio
import base64
import json
import logging
from typing import Optional

from .browser_manager import get_manager

logger = logging.getLogger(__name__)


def _parse_ref(ref: str) -> str:
    """Convert @e12 style ref to CSS selector for Playwright."""
    # Store element refs from snapshot for later use
    return ref


async def tool_launch(
    headless: bool = True,
    proxy: Optional[str] = None,
    humanize: bool = True,
    user_agent: Optional[str] = None,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    locale: Optional[str] = None,
    fingerprint_seed: Optional[str] = None,
    geoip: bool = True,
) -> str:
    """Launch a stealth CloakBrowser instance.

    Anti-detection features are ON by default. Explicitly pass
    headless=True, humanize=False, or geoip=False to disable.

    Args:
        headless: Run in headless mode. Default True.
        proxy: Proxy URL (http/socks5).
        humanize: Human-like mouse/keyboard. Default True.
        user_agent: Custom User-Agent string.
        viewport_width: Viewport width in pixels.
        viewport_height: Viewport height in pixels.
        locale: Browser locale (e.g. 'en-US', 'zh-CN').
        fingerprint_seed: Deterministic fingerprint seed for consistent identity.
        geoip: Auto-detect timezone/locale from proxy IP. Default True.
    """
    mgr = get_manager()
    await mgr.ensure_browser(
        headless=headless,
        proxy=proxy,
        humanize=humanize,
        user_agent=user_agent,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        locale=locale,
        fingerprint_seed=fingerprint_seed,
        geoip=geoip,
    )
    return "Browser launched successfully."


async def tool_close() -> str:
    """Close the browser and clean up resources."""
    mgr = get_manager()
    await mgr.close()
    return "Browser closed."


async def tool_navigate(url: str) -> str:
    """Navigate to a URL and return a compact snapshot of the page.

    Args:
        url: The URL to navigate to.
    """
    mgr = get_manager()
    if not mgr.is_running:
        await mgr.ensure_browser()

    # Use domcontentloaded to avoid timeout on pages with persistent
    # connections (WebSocket, long-polling, ads, analytics, etc.)
    response = await mgr.page.goto(url, wait_until="domcontentloaded", timeout=30000)
    status = response.status if response else "unknown"

    # Best-effort: try waiting for networkidle with a short timeout.
    # Many real-world pages (Discourse, forums, SPAs) never reach
    # networkidle due to background connections, so we gracefully
    # fall back to dom-ready + a small fixed delay.
    try:
        await mgr.page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        try:
            await mgr.page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass

    # Get full snapshot (page content + interactive elements) so the
    # model has full context of the new page after navigation.
    snapshot = await _get_snapshot(mgr, full=True)
    return f"Navigation status: {status}\n\n{snapshot}"


async def tool_snapshot(full: bool = False) -> str:
    """Get a text-based snapshot of the current page's accessibility tree.

    Args:
        full: If true, return complete page content. If false, return compact view.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."
    return await _get_snapshot(mgr, full=full)


async def _get_snapshot(mgr, full: bool = False) -> str:
    """Build a text snapshot of the page with ref IDs for interactive elements."""
    page = mgr.page
    try:
        # Wait briefly for dynamic content to render (JS frameworks, AJAX)
        try:
            await page.wait_for_function(
                "() => document.readyState === 'complete'",
                timeout=5000,
            )
        except Exception:
            pass

        # Small additional wait for JS hydration (React, Vue, Angular)
        try:
            await page.wait_for_timeout(500)
        except Exception:
            pass

        # Get all interactive elements with refs
        elements = await page.evaluate("""() => {
            const interactive = document.querySelectorAll(
                'a, button, input, textarea, select, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [contenteditable="true"], details, summary, label'
            );
            const results = [];
            let idx = 1;
            for (const el of interactive) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) continue;

                const tag = el.tagName.toLowerCase();
                const text = (el.textContent || '').trim().substring(0, 100);
                const value = el.value || '';
                const placeholder = el.placeholder || '';
                const href = el.href || '';
                const role = el.getAttribute('role') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                const type = el.type || '';
                const ref = `@e${idx}`;

                el.setAttribute('data-cloak-ref', ref);

                results.push({
                    ref, tag, text, value, placeholder, href, role, ariaLabel, type,
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    width: Math.round(rect.width), height: Math.round(rect.height),
                });
                idx++;
            }
            return results;
        }""")

        # Build snapshot text
        lines = []
        if not full:
            lines.append(f"Page: {await page.title()}")
            lines.append(f"URL: {page.url}")
            lines.append("")
            lines.append("Interactive elements:")
            for el in elements[:100]:  # Limit for compact view
                ref = el["ref"]
                tag = el["tag"]
                text = el["text"] or el["ariaLabel"] or el["placeholder"] or ""
                extra = ""
                if el["href"]:
                    extra = f" -> {el['href'][:80]}"
                if el["value"] and tag in ("input", "textarea"):
                    extra += f" [value: {el['value'][:50]}]"
                if el["type"]:
                    extra += f" [type: {el['type']}]"
                lines.append(f"  [{ref}] <{tag}>{text}{extra}")
        else:
            # Full content: get visible text + interactive elements
            body_text = await page.evaluate("""() => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: (node) => {
                            const parent = node.parentElement;
                            if (!parent) return NodeFilter.FILTER_REJECT;
                            const style = window.getComputedStyle(parent);
                            if (style.display === 'none' || style.visibility === 'hidden') return NodeFilter.FILTER_REJECT;
                            const text = node.textContent.trim();
                            if (!text) return NodeFilter.FILTER_REJECT;
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );
                const texts = [];
                while (walker.nextNode()) {
                    texts.push(walker.currentNode.textContent.trim());
                }
                return texts.join('\\n');
            }""")

            lines.append(f"Page: {await page.title()}")
            lines.append(f"URL: {page.url}")
            lines.append("")
            lines.append("Page content:")
            lines.append(body_text[:8000])
            lines.append("")
            lines.append("Interactive elements:")
            for el in elements[:200]:
                ref = el["ref"]
                tag = el["tag"]
                text = el["text"] or el["ariaLabel"] or el["placeholder"] or ""
                extra = ""
                if el["href"]:
                    extra = f" -> {el['href'][:80]}"
                if el["value"] and tag in ("input", "textarea"):
                    extra += f" [value: {el['value'][:50]}]"
                if el["type"]:
                    extra += f" [type: {el['type']}]"
                lines.append(f"  [{ref}] <{tag}>{text}{extra}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting snapshot: {e}"


async def tool_click(ref: str) -> str:
    """Click on an element identified by its ref ID from the snapshot.

    Args:
        ref: The element reference (e.g. '@e5').
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        element = await _find_element(mgr, ref)
        if not element:
            return f"Error: Element {ref} not found."
        await element.click(timeout=5000)
        await mgr.page.wait_for_load_state("domcontentloaded", timeout=5000)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Clicked {ref}.\n\n{snapshot}"
    except Exception as e:
        return f"Error clicking {ref}: {e}"


async def tool_type(ref: str, text: str, submit: bool = False) -> str:
    """Type text into an input field identified by its ref ID.

    Args:
        ref: The element reference (e.g. '@e3').
        text: The text to type.
        submit: If true, press Enter after typing.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        element = await _find_element(mgr, ref)
        if not element:
            return f"Error: Element {ref} not found."
        await element.click()
        await element.fill("")
        await element.type(text, delay=50)
        if submit:
            await element.press("Enter")
            await mgr.page.wait_for_load_state("domcontentloaded", timeout=5000)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Typed text into {ref}.{ ' Submitted.' if submit else ''}\n\n{snapshot}"
    except Exception as e:
        return f"Error typing into {ref}: {e}"


async def tool_press(key: str) -> str:
    """Press a keyboard key.

    Args:
        key: Key to press (e.g. 'Enter', 'Tab', 'Escape', 'ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight').
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        await mgr.page.keyboard.press(key)
        await asyncio.sleep(0.5)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Pressed {key}.\n\n{snapshot}"
    except Exception as e:
        return f"Error pressing {key}: {e}"


async def tool_scroll(direction: str = "down") -> str:
    """Scroll the page in a direction.

    Args:
        direction: Direction to scroll ('up' or 'down').
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        delta = 500 if direction == "down" else -500
        await mgr.page.mouse.wheel(0, delta)
        await asyncio.sleep(0.5)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Scrolled {direction}.\n\n{snapshot}"
    except Exception as e:
        return f"Error scrolling: {e}"


async def tool_back() -> str:
    """Navigate back in browser history."""
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        await mgr.page.go_back(timeout=10000)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Navigated back.\n\n{snapshot}"
    except Exception as e:
        return f"Error navigating back: {e}"


async def tool_forward() -> str:
    """Navigate forward in browser history."""
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        await mgr.page.go_forward(timeout=10000)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Navigated forward.\n\n{snapshot}"
    except Exception as e:
        return f"Error navigating forward: {e}"


async def tool_console(clear: bool = False, expression: Optional[str] = None) -> str:
    """Get browser console output or evaluate JavaScript.

    Args:
        clear: Clear the console log buffer after reading.
        expression: JavaScript expression to evaluate in the page context.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        if expression:
            result = await mgr.page.evaluate(expression)
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False, indent=2)
            return str(result)
        else:
            logs = mgr.get_console_logs(clear=clear)
            if not logs:
                return "No console messages."
            return "\n".join(logs[-50:])  # Last 50 messages
    except Exception as e:
        return f"Error: {e}"


async def tool_get_images() -> str:
    """Get a list of all images on the current page with their URLs and alt text.

    Returns a JSON list of {url, alt, width, height} objects.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        images = await mgr.page.evaluate("""() => {
            const imgs = document.querySelectorAll('img');
            return Array.from(imgs).map(img => ({
                url: img.src || img.dataset.src || '',
                alt: img.alt || '',
                width: img.naturalWidth || img.width || 0,
                height: img.naturalHeight || img.height || 0,
            })).filter(img => img.url && !img.url.startsWith('data:'));
        }""")
        return json.dumps(images, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error getting images: {e}"


async def tool_screenshot(
    question: Optional[str] = None,
    annotate: bool = False,
) -> dict:
    """Take a screenshot of the current page and return the image.

    Args:
        question: What you want to know about the page visually.
        annotate: If true, overlay numbered labels on interactive elements.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return {"error": "No browser running. Call cloak_launch first."}

    try:
        if annotate:
            # Add numbered labels to interactive elements
            await mgr.page.evaluate("""() => {
                document.querySelectorAll('[data-cloak-ref]').forEach(el => {
                    const ref = el.getAttribute('data-cloak-ref');
                    const num = ref.replace('@e', '');
                    const rect = el.getBoundingClientRect();
                    const label = document.createElement('div');
                    label.textContent = `[${num}]`;
                    label.style.cssText = `
                        position: fixed;
                        left: ${rect.left}px;
                        top: ${rect.top - 16}px;
                        background: #ff4444;
                        color: white;
                        font-size: 11px;
                        padding: 1px 4px;
                        border-radius: 3px;
                        z-index: 999999;
                        pointer-events: none;
                        font-family: monospace;
                    `;
                    document.body.appendChild(label);
                });
            }""")

        screenshot_bytes = await mgr.page.screenshot(type="png")
        b64 = base64.b64encode(screenshot_bytes).decode()

        # Clean up annotations
        if annotate:
            await mgr.page.evaluate("""() => {
                document.querySelectorAll('div[style*="z-index: 999999"]').forEach(el => el.remove());
            }""")

        return {
            "type": "image",
            "data": b64,
            "format": "png",
            "question": question or "Describe this screenshot.",
        }
    except Exception as e:
        return {"error": f"Error taking screenshot: {e}"}


async def tool_wait_for(
    selector: Optional[str] = None,
    text: Optional[str] = None,
    timeout: int = 10000,
) -> str:
    """Wait for an element or text to appear on the page.

    Args:
        selector: CSS selector to wait for.
        text: Text content to wait for.
        timeout: Timeout in milliseconds (default: 10000).
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        if selector:
            await mgr.page.wait_for_selector(selector, timeout=timeout)
            return f"Element '{selector}' appeared."
        elif text:
            await mgr.page.wait_for_function(
                f"document.body.innerText.includes('{text}')",
                timeout=timeout,
            )
            return f"Text '{text}' appeared."
        else:
            return "Error: Must provide either 'selector' or 'text'."
    except Exception as e:
        return f"Timeout waiting for {'selector' if selector else 'text'}: {e}"


async def tool_evaluate(expression: str) -> str:
    """Evaluate JavaScript expression in the page context.

    Args:
        expression: JavaScript expression to evaluate.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        result = await mgr.page.evaluate(expression)
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"


async def tool_get_content(
    selector: str = "body",
    text_only: bool = True,
    max_length: int = 10000,
) -> str:
    """Get content of an element or the entire page.

    When text_only=True (default), returns clean visible text with
    excessive whitespace collapsed. Style/script tags are excluded.

    When text_only=False, returns innerHTML with <style>, <script>,
    and <noscript> tags stripped.

    Args:
        selector: CSS selector (default: 'body' for entire page).
        text_only: If true, return clean text. If false, return cleaned HTML.
        max_length: Maximum content length in characters.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        element = await mgr.page.query_selector(selector)
        if not element:
            return f"Error: Element '{selector}' not found."

        if text_only:
            # Use TreeWalker to get only visible text nodes,
            # then collapse excessive whitespace.
            content = await mgr.page.evaluate(
                """([sel, maxLen]) => {
                    const root = document.querySelector(sel) || document.body;
                    const walker = document.createTreeWalker(
                        root,
                        NodeFilter.SHOW_TEXT,
                        {
                            acceptNode: (node) => {
                                const parent = node.parentElement;
                                if (!parent) return NodeFilter.FILTER_REJECT;
                                // Skip style, script, noscript, template
                                const tag = parent.tagName.toLowerCase();
                                if (['style','script','noscript','template','head'].includes(tag))
                                    return NodeFilter.FILTER_REJECT;
                                // Skip hidden elements
                                const style = window.getComputedStyle(parent);
                                if (style.display === 'none' || style.visibility === 'hidden')
                                    return NodeFilter.FILTER_REJECT;
                                // Skip empty text
                                if (!node.textContent.trim()) return NodeFilter.FILTER_REJECT;
                                return NodeFilter.FILTER_ACCEPT;
                            }
                        }
                    );
                    const parts = [];
                    while (walker.nextNode()) {
                        parts.push(walker.currentNode.textContent.trim());
                    }
                    // Join with single newline, collapse 3+ newlines to 2
                    var text = parts.join(String.fromCharCode(10));
                    text = text.replace(/\n{3,}/g, String.fromCharCode(10,10));
                    return text.substring(0, maxLen);
                }""",
                [selector, max_length],
            )
        else:
            # Return innerHTML but strip style/script/noscript tags
            content = await mgr.page.evaluate(
                """([sel, maxLen]) => {
                    const root = document.querySelector(sel) || document.body;
                    // Clone so we don't modify the live DOM
                    const clone = root.cloneNode(true);
                    // Remove non-content tags
                    for (const tag of ['style','script','noscript','template']) {
                        clone.querySelectorAll(tag).forEach(el => el.remove());
                    }
                    return clone.innerHTML.substring(0, maxLen);
                }""",
                [selector, max_length],
            )

        return content
    except Exception as e:
        return f"Error getting content: {e}"


async def tool_extract_links() -> str:
    """Extract all links from the current page.

    Returns a JSON list of {text, href, ref} objects.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        links = await mgr.page.evaluate("""() => {
            const anchors = document.querySelectorAll('a[href]');
            return Array.from(anchors).map(a => ({
                text: (a.textContent || '').trim().substring(0, 200),
                href: a.href,
                ref: a.getAttribute('data-cloak-ref') || '',
            })).filter(l => l.href && !l.href.startsWith('javascript:'));
        }""")
        return json.dumps(links, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error extracting links: {e}"


async def tool_fill_form(
    fields: list[dict],
    submit_ref: Optional[str] = None,
) -> str:
    """Fill multiple form fields at once.

    Args:
        fields: List of {ref, value} objects identifying fields and values.
        submit_ref: Optional ref of submit button to click after filling.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    results = []
    for field in fields:
        ref = field.get("ref", "")
        value = field.get("value", "")
        try:
            element = await _find_element(mgr, ref)
            if not element:
                results.append(f"{ref}: not found")
                continue
            await element.click()
            await element.fill(value)
            results.append(f"{ref}: filled")
        except Exception as e:
            results.append(f"{ref}: error - {e}")

    if submit_ref:
        try:
            submit = await _find_element(mgr, submit_ref)
            if submit:
                await submit.click()
                await mgr.page.wait_for_load_state("domcontentloaded", timeout=5000)
                results.append(f"Submit ({submit_ref}): clicked")
        except Exception as e:
            results.append(f"Submit ({submit_ref}): error - {e}")

    snapshot = await _get_snapshot(mgr, full=False)
    return f"Form fill results:\n" + "\n".join(results) + f"\n\n{snapshot}"


async def tool_hover(ref: str) -> str:
    """Hover over an element identified by its ref ID.

    Args:
        ref: The element reference (e.g. '@e5').
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        element = await _find_element(mgr, ref)
        if not element:
            return f"Error: Element {ref} not found."
        await element.hover(timeout=5000)
        await asyncio.sleep(0.5)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Hovered over {ref}.\n\n{snapshot}"
    except Exception as e:
        return f"Error hovering over {ref}: {e}"


async def tool_select_option(ref: str, values: list[str]) -> str:
    """Select option(s) in a <select> element.

    Args:
        ref: The element reference of the <select>.
        values: List of option values to select.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        element = await _find_element(mgr, ref)
        if not element:
            return f"Error: Element {ref} not found."
        await element.select_option(values)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Selected {values} in {ref}.\n\n{snapshot}"
    except Exception as e:
        return f"Error selecting options in {ref}: {e}"


async def tool_drag(ref_from: str, ref_to: str) -> str:
    """Drag an element from one position to another.

    Args:
        ref_from: The element reference to drag from.
        ref_to: The element reference to drag to.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        src = await _find_element(mgr, ref_from)
        dst = await _find_element(mgr, ref_to)
        if not src:
            return f"Error: Source element {ref_from} not found."
        if not dst:
            return f"Error: Target element {ref_to} not found."
        await src.drag_to(dst)
        snapshot = await _get_snapshot(mgr, full=False)
        return f"Dragged {ref_from} to {ref_to}.\n\n{snapshot}"
    except Exception as e:
        return f"Error dragging: {e}"


async def tool_save_storage_state(path: str) -> str:
    """Save browser storage state (cookies, localStorage) to a JSON file.

    Args:
        path: File path to save the state.
    """
    mgr = get_manager()
    if not mgr.is_running:
        return "Error: No browser running. Call cloak_launch first."

    try:
        await mgr.context.storage_state(path=path)
        return f"Storage state saved to {path}."
    except Exception as e:
        return f"Error saving storage state: {e}"


async def tool_load_storage_state(path: str) -> str:
    """Load browser storage state (cookies, localStorage) from a JSON file.

    Args:
        path: File path to load the state from.
    """
    mgr = get_manager()
    try:
        await mgr.ensure_browser()
        # Need to create new context with storage state
        await mgr.close()
        mgr2 = get_manager()
        mgr2._context = await launch_context_async(storage_state=path)
        mgr2._page = await mgr2._context.new_page()
        mgr2._page.on("console", mgr2._on_console)
        return f"Storage state loaded from {path}."
    except Exception as e:
        return f"Error loading storage state: {e}"


async def tool_info() -> str:
    """Get information about the current browser session."""
    mgr = get_manager()
    if not mgr.is_running:
        return "Browser is not running."

    try:
        info = {
            "url": mgr.page.url,
            "title": await mgr.page.title(),
            "viewport": mgr.page.viewport_size,
            "is_closed": mgr.page.is_closed(),
        }
        return json.dumps(info, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error getting info: {e}"


async def _find_element(mgr, ref: str):
    """Find an element by its data-cloak-ref attribute."""
    selector = f'[data-cloak-ref="{ref}"]'
    return await mgr.page.query_selector(selector)
