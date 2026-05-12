# CloakBrowser MCP Server

[English](README.md) | [中文](README_CN.md)

> 基于 [Model Context Protocol](https://modelcontextprotocol.io/) 的隐身浏览器自动化服务，由 [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) 驱动。

一个即插即用的 MCP 服务器，封装了 CloakBrowser 的隐身 Chromium —— 通过 **57 个源码级 C++ 指纹补丁**（不是 JS 注入）实现浏览器伪装。通过所有 30 项反 bot 检测（reCAPTCHA v3 评分 0.9、Cloudflare Turnstile: PASS、FingerprintJS: PASS）。

所有工具使用 `cloak_` 前缀，避免与 Hermes Agent 内置的 `browser_*` 工具冲突。

## ✨ 特性

- **22 个 cloak 工具** —— 导航、点击、输入、截图、控制台、JS 执行、表单填充、拖拽等
- **默认隐身** —— `navigator.webdriver = false`，真实 Chrome TLS 指纹，无 CDP 检测
- **人机行为模拟** —— `humanize=True` 启用贝塞尔鼠标曲线、逐字符键盘节奏
- **代理支持** —— HTTP / SOCKS5，支持 GeoIP 自动地理定位
- **会话持久化** —— 保存/加载 cookies 和 localStorage
- **兼容所有 MCP 客户端** —— Hermes Agent、Claude Desktop、Cursor 等
- **无命名冲突** —— `cloak_*` 前缀不会与 Hermes 内置 `browser_*` 工具冲突

## 🚀 快速开始

### 安装

```bash
pip install mcp-cloakbrowser
```

### 运行

```bash
# 作为 stdio MCP 服务器启动
mcp-cloakbrowser

# 或者直接运行
python -m cloakbrowser_mcp.server
```

### 配合 Hermes Agent 使用

编辑 `~/.hermes/config.yaml`，添加以下配置：

```yaml
mcp_servers:
  cloakbrowser:
    command: "python"
    args: ["-m", "cloakbrowser_mcp.server"]
    timeout: 120
```

重启 Hermes Agent 后，工具会自动注册为 `mcp_cloakbrowser_cloak_*` 前缀。

### 配合 Claude Desktop 使用

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "cloakbrowser": {
      "command": "mcp-cloakbrowser"
    }
  }
}
```

## 📋 工具列表

所有工具使用 `cloak_` 前缀（在 Hermes 中注册为 `mcp_cloakbrowser_cloak_*`）：

| 工具名 | 说明 | 参数 |
|--------|------|------|
| `cloak_launch` | 启动隐身 CloakBrowser 实例 | headless, humanize, proxy, fingerprint_seed, geoip, locale |
| `cloak_close` | 关闭浏览器并清理资源 | 无 |
| `cloak_navigate` | 导航到 URL，返回页面快照 | url |
| `cloak_snapshot` | 获取页面可访问性树（含 ref ID） | full |
| `cloak_click` | 点击元素 | ref |
| `cloak_type` | 在输入框中输入文本 | ref, text, submit |
| `cloak_press` | 按下键盘按键 | key |
| `cloak_scroll` | 滚动页面 | direction (up/down) |
| `cloak_back` | 浏览器后退 | 无 |
| `cloak_forward` | 浏览器前进 | 无 |
| `cloak_console` | 获取控制台日志或执行 JS | expression, clear |
| `cloak_get_images` | 列出页面所有图片 | 无 |
| `cloak_screenshot` | 截取 PNG 截图 | question, annotate |
| `cloak_wait_for` | 等待元素或文本出现 | selector, text, timeout |
| `cloak_evaluate` | 执行 JavaScript 表达式 | expression |
| `cloak_get_content` | 获取页面/元素的文本或 HTML | selector, text_only, max_length |
| `cloak_extract_links` | 提取页面所有链接 | 无 |
| `cloak_fill_form` | 批量填充表单字段 | fields, submit_ref |
| `cloak_hover` | 鼠标悬停元素 | ref |
| `cloak_select_option` | 选择下拉框选项 | ref, values |
| `cloak_drag` | 拖拽元素到另一位置 | ref_from, ref_to |
| `cloak_save_storage_state` | 保存 cookies/localStorage | path |
| `cloak_load_storage_state` | 加载 cookies/localStorage | path |
| `cloak_info` | 获取当前页面 URL、标题、视口 | 无 |

## 💡 使用示例

### 基本导航与交互

```python
# 启动浏览器（隐身模式 + 人机模拟）
await call_tool("cloak_launch", {"headless": True, "humanize": True})

# 导航到目标页面
await call_tool("cloak_navigate", {"url": "https://example.com"})

# 获取页面快照，查看可交互元素
snapshot = await call_tool("cloak_snapshot", {})
# 输出示例: [@e1] <a>链接文字, [@e2] <input>[type: text]...

# 点击链接
await call_tool("cloak_click", {"ref": "@e1"})

# 在搜索框输入文字并回车
await call_tool("cloak_type", {"ref": "@e2", "text": "你好世界", "submit": True})

# 截图
await call_tool("cloak_screenshot", {})
```

### 填写登录表单

```python
await call_tool("cloak_fill_form", {
    "fields": [
        {"ref": "@e1", "value": "用户名"},
        {"ref": "@e2", "value": "密码123"},
    ],
    "submit_ref": "@e3",  # 点击登录按钮
})
```

### 高级：自定义指纹 + 代理

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

### 保存/恢复登录会话

```python
# 登录后保存会话
await call_tool("cloak_save_storage_state", {"path": "session.json"})

# 下次使用时恢复会话
await call_tool("cloak_load_storage_state", {"path": "session.json"})
```

## 🔑 为什么用 `cloak_` 前缀？

Hermes Agent 自带 `browser_*` 工具（browser_navigate、browser_click 等），使用内置的 Playwright 实例。如果 MCP 工具也用同样的名字会产生冲突。`cloak_` 前缀明确表示这些工具使用的是 CloakBrowser 隐身 Chromium，并且可以在同一会话中同时使用两套工具：

- `browser_navigate` → Hermes 内置 Playwright（快速，无隐身）
- `cloak_navigate` → CloakBrowser 隐身 Chromium（通过反 bot 检测）

## 🏗️ 架构

```
MCP 客户端 (Hermes / Claude / Cursor 等)
    │ stdio (JSON-RPC)
    ▼
mcp-cloakbrowser 服务器
    │
    ▼
CloakBrowser (Playwright 兼容 API)
    │
    ▼
隐身 Chromium (57 个 C++ 源码补丁)
```

服务器维护一个浏览器单例。所有工具操作当前活跃页面。首次调用工具时会自动启动浏览器（无需手动 launch）。

## 🔧 与 Hermes Agent 内置浏览器工具的区别

| 特性 | Hermes 内置 browser_* | CloakBrowser MCP cloak_* |
|------|----------------------|--------------------------|
| 反 bot 检测 | ❌ 原生 Playwright，容易被检测 | ✅ 57 个 C++ 补丁，通过全部检测 |
| navigator.webdriver | true（可被检测） | false（完全隐藏） |
| TLS 指纹 | Playwright 默认 | 真实 Chrome |
| 人机模拟 | ❌ 无 | ✅ 贝塞尔曲线鼠标 + 逐字符输入 |
| 代理 + GeoIP | ❌ 不支持 | ✅ HTTP/SOCKS5 + 地理定位 |
| 指纹种子 | ❌ 固定 | ✅ 每次随机或自定义 |
| 会话持久化 | ❌ 不支持 | ✅ 保存/加载 cookies |

## 📁 项目结构

```
cloakbrowser-mcp/
├── src/
│   └── cloakbrowser_mcp/
│       ├── __init__.py          # 版本信息
│       ├── server.py            # MCP 服务器入口（工具注册）
│       ├── tools.py             # 22 个工具的实现
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

## 🛠️ 开发

```bash
git clone https://github.com/MiwooMiwoo/cloakbrowser-mcp.git
cd cloakbrowser-mcp
pip install -e ".[dev]"
```

## 📄 许可证

MIT
