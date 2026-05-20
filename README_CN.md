# CloakBrowser MCP Server

[English](README.md) | [中文](README_CN.md)

> 基于 [Model Context Protocol](https://modelcontextprotocol.io/) 的隐身浏览器自动化服务，由 [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) 驱动。

封装了 CloakBrowser 的隐身 Chromium —— 通过 **57 个源码级 C++ 指纹补丁**（不是 JS 注入）实现浏览器伪装。通过所有 30 项反 bot 检测（reCAPTCHA v3 评分 0.9、Cloudflare Turnstile: PASS、FingerprintJS: PASS）。

两种模式：
- **默认模式** — 24 个交互式工具，完整浏览器控制（导航、点击、输入、截图等）
- **`--once` 模式** — 单工具 `cloak_fetch(url)`，自动抓取页面内容+截图，零配置

## 快速开始

### 安装与运行

无需安装，直接通过 [uvx](https://docs.astral.sh/uv/guides/tools/) 从 Git 仓库运行：

```bash
# 默认模式（完整 24 工具 MCP 服务器）
uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp

# --once 模式（单工具抓取：文本 + 截图）
uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp --once
```

首次运行会自动下载 CloakBrowser 补丁版 Chromium（约 200MB），后续启动秒开。

### 配合 Claude Desktop / Cursor 使用

编辑 `claude_desktop_mcp.json` 或 `.vscode/mcp.json`：

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

`--once` 模式只需在 args 末尾追加 `"--once"`。

### 配合 Hermes Agent 使用

编辑 `~/.hermes/config.yaml`：

```yaml
mcp_servers:
  cloakbrowser:
    command: "uvx"
    args: ["--from", "git+https://github.com/ptbsare/cloakbrowser-mcp-server", "cloakbrowser-mcp"]
    timeout: 120
```

## --once 模式（自动化爬取）

专为机器爬取设计。一个工具，一个 URL，返回一切：

```bash
# 可选：自动加载登录 cookie 和/或持久化 profile
export CLOAKBROWSER_COOKIES_FILE=/path/to/cookies.txt
export CLOAKBROWSER_USER_DATA_DIR=/path/to/browser-profile

uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp --once
```

大模型只需调用：

```
cloak_fetch(url="https://example.com")
```

返回：
- **text** — 干净的页面可见文本（已去除 CSS/JS/多余空白）
- **screenshot** — 完整页面 PNG 截图
- **url** — 最终 URL（重定向后）
- **title** — 页面标题

所有反检测参数自动启用：`headless=True`、`humanize=True`、`geoip=True`。大模型无需关心任何参数。

## 默认模式（完整自动化）

24 个交互式工具，完整浏览器控制。所有工具使用 `cloak_` 前缀，避免与 Hermes Agent 内置的 `browser_*` 工具冲突。

### 隐身默认值

`cloak_launch` 默认启用所有反检测：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `headless` | `True` | 无头模式（传 `False` 启用有头） |
| `humanize` | `True` | 贝塞尔鼠标曲线、逐字符键盘输入 |
| `geoip` | `True` | 自动从 proxy IP 检测时区/语言 |

显式传 `headless=False`、`humanize=False` 或 `geoip=False` 可关闭。

### 工具列表

| 工具名 | 说明 |
|--------|------|
| `cloak_launch` | 启动隐身浏览器（默认开启所有反检测） |
| `cloak_close` | 关闭浏览器并释放资源 |
| `cloak_navigate` | 导航到 URL，返回完整页面内容 + 可交互元素 |
| `cloak_snapshot` | 获取页面内容和带 `[@eN]` ref ID 的可交互元素 |
| `cloak_click` | 点击元素（如 `@e5`） |
| `cloak_type` | 在输入框中输入文本 |
| `cloak_press` | 按下键盘按键（Enter、Tab、Escape...） |
| `cloak_scroll` | 滚动页面 |
| `cloak_back` | 浏览器后退 |
| `cloak_forward` | 浏览器前进 |
| `cloak_console` | 获取控制台日志或执行 JS |
| `cloak_get_images` | 列出页面所有图片 |
| `cloak_screenshot` | 截取 PNG 截图 |
| `cloak_wait_for` | 等待元素或文本出现 |
| `cloak_evaluate` | 执行 JavaScript 表达式 |
| `cloak_get_content` | 获取页面/元素的干净文本或 HTML |
| `cloak_extract_links` | 提取所有链接为 JSON |
| `cloak_fill_form` | 批量填充表单字段 |
| `cloak_hover` | 鼠标悬停元素 |
| `cloak_select_option` | 选择下拉框选项 |
| `cloak_drag` | 拖拽元素到另一位置 |
| `cloak_save_storage_state` | 保存 cookies/localStorage 到 JSON 文件 |
| `cloak_load_storage_state` | 从 JSON 文件加载 cookies/localStorage |
| `cloak_info` | 获取当前页面 URL、标题、视口 |

### 使用示例

#### 基本导航与交互

```python
# 启动浏览器（隐身默认值自动启用）
await call_tool("cloak_launch", {})

# 导航到目标页面 — 返回完整内容 + 可交互元素
result = await call_tool("cloak_navigate", {"url": "https://example.com"})

# 获取带 ref ID 的页面快照
snapshot = await call_tool("cloak_snapshot", {})
# 输出: [@e1] <a>链接文字, [@e2] <input>[type: text]...

# 点击链接
await call_tool("cloak_click", {"ref": "@e1"})

# 在搜索框输入并回车
await call_tool("cloak_type", {"ref": "@e2", "text": "你好世界", "submit": True})

# 截图
await call_tool("cloak_screenshot", {})
```

#### 填写登录表单

```python
await call_tool("cloak_fill_form", {
    "fields": [
        {"ref": "@e1", "value": "用户名"},
        {"ref": "@e2", "value": "密码123"},
    ],
    "submit_ref": "@e3",  # 点击登录按钮
})
```

#### 自定义指纹 + 代理

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

#### 保存/恢复登录会话

```python
# 登录后保存会话
await call_tool("cloak_save_storage_state", {"path": "session.json"})

# 下次使用时恢复会话
await call_tool("cloak_load_storage_state", {"path": "session.json"})
```

## Cookie 管理

### 自动加载 Cookie（所有模式）

设置环境变量后，每次启动浏览器时自动加载：

```bash
export CLOAKBROWSER_COOKIES_FILE=/path/to/cookies.txt
```

支持标准 Netscape cookie.txt 格式（tab 分隔），可从以下方式导出：
- Chrome 插件：EditThisCookie、cookie-editor
- Firefox 插件：cookies.txt
- 命令行工具：`yt-dlp --cookies cookies.txt` 等

文件格式：
```
.example.com	TRUE	/	TRUE	1735689600	session_id	abc123xyz
.example.com	TRUE	/	FALSE	0	user_pref	dark_mode
```

对大模型完全透明，无需额外工具调用。

### 持久化浏览器 Profile

设置 `CLOAKBROWSER_USER_DATA_DIR` 为目录路径，浏览器状态（cookie、localStorage、登录态、Cloudflare 验证）将在重启后自动保留。登录一次，永久有效：

```bash
export CLOAKBROWSER_USER_DATA_DIR=/path/to/browser-profile
```

底层使用 Playwright 的 `user_data_dir` 机制，目录不存在时自动创建。

**推荐工作流：**
1. 设置 `CLOAKBROWSER_USER_DATA_DIR` 和 `CLOAKBROWSER_COOKIES_FILE`
2. 启动浏览器并手动登录（或通过 `cloak_fill_form` 自动填写）
3. 后续启动自动保留登录态，无需重新导入 cookie

两者结合使用效果最佳：
```bash
export CLOAKBROWSER_USER_DATA_DIR=/path/to/browser-profile
export CLOAKBROWSER_COOKIES_FILE=/path/to/cookies.txt
uvx --from git+https://github.com/ptbsare/cloakbrowser-mcp-server cloakbrowser-mcp
```

## 为什么用 `cloak_` 前缀？

Hermes Agent 自带 `browser_*` 工具（browser_navigate、browser_click 等），使用内置的 Playwright 实例。`cloak_` 前缀避免命名冲突，且两者可在同一会话中共存：

- `browser_navigate` → Hermes 内置 Playwright（快速，无隐身）
- `cloak_navigate` → CloakBrowser 隐身 Chromium（通过反 bot 检测）

## 架构

```
MCP 客户端 (Hermes / Claude / Cursor 等)
    │ stdio (JSON-RPC)
    ▼
cloakbrowser-mcp 服务器
    │
    ├── 默认模式：24 个交互式工具
    └── --once 模式：1 个抓取工具 (cloak_fetch)
    │
    ▼
CloakBrowser (Playwright 兼容 API)
    │
    ▼
隐身 Chromium (57 个 C++ 源码补丁)
```

服务器维护浏览器单例。默认模式下浏览器在工具调用间保持；`--once` 模式下每次抓取后自动关闭。

## 与 Hermes 内置浏览器工具的区别

| 特性 | Hermes 内置 browser_* | CloakBrowser MCP cloak_* |
|------|----------------------|--------------------------|
| 反 bot 检测 | ❌ 原生 Playwright，容易被检测 | ✅ 57 个 C++ 补丁，通过全部检测 |
| navigator.webdriver | true（可被检测） | false（完全隐藏） |
| TLS 指纹 | Playwright 默认 | 真实 Chrome |
| 人机模拟 | ❌ 无 | ✅ 贝塞尔曲线鼠标 + 逐字符输入 |
| 代理 + GeoIP | ❌ 不支持 | ✅ HTTP/SOCKS5 + 地理定位 |
| 指纹种子 | ❌ 固定 | ✅ 每次随机或自定义 |
| 会话持久化 | ❌ 不支持 | ✅ 保存/加载 cookies |

## 项目结构

```
cloakbrowser-mcp-server/
├── src/
│   └── cloakbrowser_mcp/
│       ├── __init__.py          # 版本信息
│       ├── server.py            # MCP 服务器入口（工具注册、模式切换）
│       ├── tools.py             # 工具实现（24 个交互工具 + cloak_fetch）
│       └── browser_manager.py   # 浏览器生命周期管理（单例）
├── examples/
│   └── hermes_config.yaml       # Hermes Agent 配置示例
├── skills/
│   └── cloakbrowser-mcp/
│       └── SKILL.md             # 配套 Hermes Skill 文件
├── pyproject.toml               # 打包配置
├── README.md                    # 英文文档
├── README_CN.md                 # 中文文档（本文件）
└── LICENSE                      # MIT 许可证
```

## 开发

```bash
git clone https://github.com/ptbsare/cloakbrowser-mcp-server
cd cloakbrowser-mcp-server
pip install -e ".[dev]"
```

## 许可证

MIT
