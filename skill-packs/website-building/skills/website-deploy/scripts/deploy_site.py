#!/usr/bin/env python3
"""官網部署工具：Wrangler 登入檢查、部署預覽、部署、HTTP 讀回、自訂網域設定與正式公開。只用標準函式庫。

所有會改變外部狀態的命令（deploy）與會改寫專案檔的命令（domain apply、publish）都需要確認旗標；
旗標只是防誤用，不取代 Agent 在對話中取得使用者授權。本工具不保存任何 Token；登入狀態由 Wrangler 自己管理。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_WRANGLER_VERSION = "4.129.0"
WORKER_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
DOMAIN_PATTERN = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
WORKERS_DEV_URL = re.compile(r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.workers\.dev")
ANY_HTTPS_URL = re.compile(r"https://[a-z0-9.-]+\.[a-z]{2,63}/?")
REQUIRED_PATHS = ("/", "/about/", "/services/", "/blog/", "/contact/")
REQUIRED_FILES = ("/rss.xml", "/sitemap-index.xml", "/favicon.svg", "/og-image.png")
ZONE_EDIT_SCOPES = ("zone (edit)", "zone:edit", "zone (write)", "zone:write")


class DeployError(RuntimeError):
    """表示必須停止且不應繼續外部操作的錯誤。"""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def wrangler_command() -> list[str]:
    """決定 wrangler 執行方式。測試用 WEBSITE_WRANGLER_BIN 指向假程式；正式用專案內鎖定版本。"""

    override = os.environ.get("WEBSITE_WRANGLER_BIN")
    if override:
        return [override]
    return ["npx", "--no-install", "wrangler"]


def run_wrangler(project: Path, arguments: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    """在專案目錄執行 wrangler，環境變數只保留必要項目，不注入任何 Token。"""

    allowed = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "WRANGLER_HOME", "XDG_CONFIG_HOME", "CI", "NODE_OPTIONS", "npm_config_cache")
    env = {key: value for key, value in os.environ.items() if key in allowed or key.startswith(("WEBSITE_", "FAKE_WRANGLER_"))}
    env["CI"] = "1"  # 避免互動式提示卡住；需要互動的情況由 Agent 另行處理
    try:
        return subprocess.run(wrangler_command() + arguments, cwd=project, capture_output=True, text=True, timeout=timeout, env=env)
    except FileNotFoundError as error:
        raise DeployError(f"找不到 wrangler：{error}；請先在專案執行 npm ci") from error
    except subprocess.TimeoutExpired as error:
        raise DeployError(f"wrangler {' '.join(arguments)} 超過 {timeout} 秒未完成") from error


def validate_project(raw: str) -> Path:
    project = Path(raw).expanduser().resolve(strict=False)
    if not project.is_dir():
        raise DeployError(f"專案目錄不存在：{project}")
    for name in ("wrangler.jsonc", "site.config.mjs", "package.json"):
        target = project / name
        if target.is_symlink() or not target.is_file():
            raise DeployError(f"專案缺少 {name}")
    return project


def strip_jsonc(text: str) -> str:
    """移除 // 與 /* */ 註解（字串內的不動），讓 json.loads 能讀 wrangler.jsonc。"""

    out: list[str] = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if ch == '"':
                in_string = False
            i += 1; continue
        if ch == '"':
            in_string = True; out.append(ch); i += 1; continue
        if text.startswith("//", i):
            j = text.find("\n", i); i = n if j < 0 else j; continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        out.append(ch); i += 1
    cleaned = "".join(out)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)  # 容忍尾逗號
    return cleaned


def read_wrangler_config(project: Path) -> dict[str, Any]:
    raw = (project / "wrangler.jsonc").read_text(encoding="utf-8")
    try:
        config = json.loads(strip_jsonc(raw))
    except json.JSONDecodeError as error:
        raise DeployError(f"wrangler.jsonc 無法解析：{error}") from error
    name = config.get("name")
    if not isinstance(name, str) or not WORKER_NAME.fullmatch(name):
        raise DeployError("wrangler.jsonc 的 name 必須是小寫字母、數字與連字號，且不以連字號開頭或結尾")
    if "assets" not in config or not isinstance(config["assets"], dict) or config["assets"].get("directory") != "./dist":
        raise DeployError("wrangler.jsonc 必須只宣告 assets.directory 為 ./dist")
    for forbidden in ("kv_namespaces", "d1_databases", "r2_buckets", "account_id", "main"):
        if forbidden in config:
            raise DeployError(f"wrangler.jsonc 不得包含 {forbidden}；本套件只部署靜態資產且不寫入帳號識別碼")
    return config


def write_wrangler_config(project: Path, config: dict[str, Any]) -> None:
    header = (
        "// 靜態站點部署設定：只上傳 astro build 產出的 dist/。\n"
        "// 不使用 SSR adapter、不綁定 KV／D1／R2，維持免費方案。\n"
        "// routes 由 website-deploy 在使用者授權自訂網域後寫入；請勿加入 account_id 或任何秘密。\n"
    )
    (project / "wrangler.jsonc").write_text(header + json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_site_config(project: Path) -> dict[str, str]:
    """只讀取 site.config.mjs 裡部署需要的三個欄位，不執行 JavaScript。"""

    text = (project / "site.config.mjs").read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    for key in ("url", "indexing", "theme", "name"):
        match = re.search(rf"^\s*{key}:\s*'((?:[^'\\]|\\.)*)'", text, re.MULTILINE)
        if not match:
            raise DeployError(f"site.config.mjs 找不到 {key} 欄位")
        fields[key] = match.group(1).replace("\\'", "'")
    if fields["indexing"] not in ("noindex", "index"):
        raise DeployError("site.config.mjs 的 indexing 必須是 noindex 或 index")
    return fields


def set_site_field(project: Path, key: str, value: str) -> None:
    path = project / "site.config.mjs"
    text = path.read_text(encoding="utf-8")
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    updated, count = re.subn(rf"^(\s*{key}:\s*)'(?:[^'\\]|\\.)*'", rf"\g<1>'{escaped}'", text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise DeployError(f"無法更新 site.config.mjs 的 {key}")
    path.write_text(updated, encoding="utf-8")


def dist_stats(project: Path) -> dict[str, Any]:
    dist = project / "dist"
    if not dist.is_dir() or not (dist / "index.html").is_file():
        raise DeployError("找不到 dist/index.html；請先執行 npm run build")
    files = [path for path in dist.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    newest_src = max((path.stat().st_mtime for path in (project / "src").rglob("*") if path.is_file()), default=0)
    newest_src = max(newest_src, (project / "site.config.mjs").stat().st_mtime)
    newest_dist = max(path.stat().st_mtime for path in files)
    return {"files": len(files), "bytes": total, "megabytes": round(total / 1_000_000, 2), "stale": newest_src > newest_dist}


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}"


def parse_whoami(output: str) -> dict[str, Any]:
    """解析 wrangler whoami 的文字輸出，只保留非敏感摘要。"""

    lowered = output.lower()
    if "not authenticated" in lowered or "not logged in" in lowered or "wrangler login" in lowered and "logged in" not in lowered:
        return {"logged_in": False, "email_masked": None, "accounts": [], "scopes": [], "zone_edit": False}
    email_match = re.search(r"email\s+([\w.+-]+@[\w-]+(?:\.[\w-]+)+)", output)
    email = mask_email(email_match.group(1)) if email_match else None
    accounts: list[str] = []
    for line in output.splitlines():
        cells = [cell.strip() for cell in line.split("│") if cell.strip()]
        if len(cells) == 2 and re.fullmatch(r"[0-9a-f]{32}", cells[1]):
            accounts.append(cells[0])  # 只記帳號名稱，不記帳號 ID
    scopes = [line.strip()[2:].strip() for line in output.splitlines() if line.strip().startswith("- ")]
    zone_edit = any(scope.lower().startswith(prefix) for scope in scopes for prefix in ZONE_EDIT_SCOPES)
    return {"logged_in": True, "email_masked": email, "accounts": accounts, "scopes": scopes, "zone_edit": zone_edit}


def command_status(project: Path) -> dict[str, Any]:
    """唯讀：確認 wrangler 可用與登入狀態，不觸發登入。"""

    result = run_wrangler(project, ["whoami"], timeout=120)
    combined = result.stdout + "\n" + result.stderr
    parsed = parse_whoami(combined)
    version = re.search(r"wrangler\s+(\d+\.\d+\.\d+)", combined)
    return {
        "result": "logged_in" if parsed["logged_in"] else "login_required",
        "wrangler_version": version.group(1) if version else None,
        "wrangler_exit_code": result.returncode,
        **parsed,
        "human_step": None if parsed["logged_in"] else "由 Agent 執行 npx wrangler login，使用者在瀏覽器點一次「允許」；沒有帳號的人先在同一頁註冊。",
        "contains_credentials": False,
    }


def load_config(config_path: Path | None) -> dict[str, Any] | None:
    if config_path is None:
        return None
    if config_path.is_symlink() or not config_path.is_file():
        raise DeployError(f"官網設定必須是一般檔案：{config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def command_plan(project: Path, config: dict[str, Any] | None, stage: str) -> dict[str, Any]:
    """產生部署預覽：目標、網址、上傳量、費用、剩餘人類步驋。不執行任何外部操作。"""

    wrangler = read_wrangler_config(project)
    site = read_site_config(project)
    stats = dist_stats(project)
    routes = [route.get("pattern") for route in wrangler.get("routes", []) if isinstance(route, dict) and route.get("custom_domain")]
    warnings: list[str] = []
    if stats["stale"]:
        warnings.append("dist/ 比 src/ 或 site.config.mjs 舊，部署前請重新 npm run build")
    if stage == "workers_dev" and site["indexing"] != "noindex":
        raise DeployError("首次部署到 workers.dev 時 site.indexing 必須維持 noindex；正式公開請走 publish 階段")
    if stage == "publish" and site["indexing"] != "index":
        raise DeployError("publish 階段的 site.indexing 必須已改為 index；請先執行 publish 命令")
    human_steps = []
    if stage == "workers_dev":
        human_steps = ["若帳號尚未有 workers.dev 子網域：在 Cloudflare 後台 Workers & Pages 頁取一次名稱", "授權首次部署（會建立公開連結）"]
    elif stage == "custom_domain":
        human_steps = ["授權綁定自訂網域"]
    elif stage == "publish":
        human_steps = ["授權移除 noindex，讓搜尋引擎可以收錄"]
    domain_block = config.get("hosting", {}).get("custom_domain", {}) if config else {}
    return {
        "result": "plan",
        "stage": stage,
        "worker_name": wrangler["name"],
        "expected_workers_dev_url": f"https://{wrangler['name']}.<帳號子網域>.workers.dev",
        "custom_domain_routes": routes,
        "site_url_in_config": site["url"],
        "indexing": site["indexing"],
        "theme": site["theme"],
        "upload": {"files": stats["files"], "megabytes": stats["megabytes"]},
        "cost": "Cloudflare Workers 免費方案；靜態資產部署不產生費用",
        "domain_intent": {"wanted": domain_block.get("wanted"), "route": domain_block.get("acquisition_route"), "domain": domain_block.get("domain")},
        "warnings": warnings,
        "human_steps_remaining": human_steps,
        "command": "npx wrangler deploy",
        "contains_credentials": False,
    }


def command_deploy(project: Path, *, confirmed: bool, expect_indexing: str) -> dict[str, Any]:
    """執行 wrangler deploy，解析輸出中的公開網址。"""

    if not confirmed:
        raise DeployError("缺少 --confirm-deploy；未執行任何部署")
    read_wrangler_config(project)
    site = read_site_config(project)
    if site["indexing"] != expect_indexing:
        raise DeployError(f"site.indexing 是 {site['indexing']}，與預期的 {expect_indexing} 不同；停止部署")
    stats = dist_stats(project)
    if stats["stale"]:
        raise DeployError("dist/ 比來源舊；請先 npm run build 再部署")
    result = run_wrangler(project, ["deploy"])
    combined = result.stdout + "\n" + result.stderr
    if result.returncode != 0:
        tail = combined.strip().splitlines()[-12:]
        return {"result": "failed", "exit_code": result.returncode, "output_tail": tail, "contains_credentials": False}
    workers_dev = sorted(set(WORKERS_DEV_URL.findall(combined)))
    custom = sorted({url.rstrip("/") for url in ANY_HTTPS_URL.findall(combined) if ".workers.dev" not in url and "cloudflare.com" not in url and "dash.cloudflare" not in url})
    version_match = re.search(r"Current Version ID:\s*([0-9a-f-]+)", combined)
    if not workers_dev and not custom:
        return {"result": "deployed_url_unknown", "exit_code": 0, "output_tail": combined.strip().splitlines()[-12:], "note": "wrangler 未輸出網址；請用 verify 指定網址讀回，不要假設已上線", "contains_credentials": False}
    return {
        "result": "deployed",
        "workers_dev_urls": workers_dev,
        "custom_domain_urls": custom,
        "version_id": version_match.group(1) if version_match else None,
        "indexing": site["indexing"],
        "deployed_at": utc_now(),
        "next": "以 verify --url <網址> 讀回，通過後才更新設定檔的 verification 欄位",
        "contains_credentials": False,
    }


def fetch(url: str, *, method: str = "GET", timeout: int = 20) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "ai-workflow-toolbox-website-deploy/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read() if method == "GET" else b""
            return response.status, {key.lower(): value for key, value in response.headers.items()}, body
    except urllib.error.HTTPError as error:
        return error.code, {key.lower(): value for key, value in error.headers.items()}, b""
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as error:
        raise DeployError(f"無法連線 {url}：{error}") from error


def command_verify(url: str, *, expect_indexing: str) -> dict[str, Any]:
    """從公開網址讀回：必要頁面 200、404 頁、RSS、sitemap、robots、OG。"""

    base = url.rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://127.0.0.1") and not base.startswith("http://localhost"):
        raise DeployError("verify 只接受 https:// 網址（本機測試允許 127.0.0.1／localhost）")
    findings: list[dict[str, str]] = []
    checks: dict[str, Any] = {}
    for path in REQUIRED_PATHS + REQUIRED_FILES:
        status, headers, body = fetch(base + path)
        checks[path] = status
        if status != 200:
            findings.append({"kind": "unexpected_status", "detail": f"{path} -> {status}"})
        if path == "/":
            html = body.decode("utf-8", errors="replace")
            robots = re.search(r'<meta name="robots" content="([^"]+)"', html)
            expected = "index, follow" if expect_indexing == "index" else "noindex, nofollow"
            checks["robots"] = robots.group(1) if robots else None
            if not robots or robots.group(1) != expected:
                findings.append({"kind": "robots_mismatch", "detail": f"首頁 robots 是 {checks['robots']}，預期 {expected}"})
            og = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            checks["og_image"] = og.group(1) if og else None
            if not og:
                findings.append({"kind": "missing_og_image", "detail": "首頁缺少 og:image"})
            elif og.group(1).startswith("https://example.invalid"):
                findings.append({"kind": "placeholder_site_url", "detail": "og:image 仍指向 example.invalid；site.url 尚未更新為正式網址"})
    # 從 sitemap 找任一篇文章讀回；沒有文章就跳過，不假設範例文章存在
    try:
        status, _, sitemap_body = fetch(base + "/sitemap-0.xml")
        post_urls = [loc for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap_body.decode("utf-8", errors="replace")) if "/blog/" in loc and not loc.rstrip("/").endswith("/blog")]
    except DeployError:
        post_urls = []
    if post_urls:
        first = post_urls[0]
        path = "/" + first.split("/", 3)[3] if first.count("/") >= 3 else "/blog/"
        status, _, _ = fetch(base + path)
        checks[path] = status
        if status != 200:
            findings.append({"kind": "unexpected_status", "detail": f"{path} -> {status}"})
    else:
        checks["blog_post"] = "none_in_sitemap"
    status, _, _ = fetch(base + "/this-page-should-not-exist-9f3c/")
    checks["/missing"] = status
    if status != 404:
        findings.append({"kind": "custom_404_not_served", "detail": f"不存在的路徑回 {status}，預期 404"})
    return {
        "result": "verified" if not findings else "failed",
        "url": base,
        "expected_indexing": expect_indexing,
        "checks": checks,
        "findings": findings,
        "verified_at": utc_now(),
        "not_covered": ["screenshots", "dns_propagation_timing", "search_engine_indexing"],
        "contains_credentials": False,
    }


def nameservers(domain: str) -> list[str] | None:
    """用系統的 nslookup 查 NS，沒有工具就回 None。只讀，不改任何設定。"""

    tool = shutil.which("nslookup")
    if not tool:
        return None
    try:
        result = subprocess.run([tool, "-type=ns", domain], capture_output=True, text=True, timeout=20)
    except (subprocess.TimeoutExpired, OSError):
        return None
    servers = re.findall(r"nameserver\s*=\s*([a-z0-9.-]+)\.?", result.stdout, re.IGNORECASE)
    return sorted({server.lower().rstrip(".") for server in servers})


def command_domain_check(domain: str) -> dict[str, Any]:
    """唯讀：網域是否解析、NS 是否已指向 Cloudflare。"""

    if not DOMAIN_PATTERN.fullmatch(domain):
        raise DeployError("網域格式不正確")
    servers = nameservers(domain)
    on_cloudflare = None if servers is None else any(server.endswith("cloudflare.com") for server in servers)
    try:
        resolved = bool(socket.getaddrinfo(domain, 443))
    except OSError:
        resolved = False
    return {
        "result": "checked",
        "domain": domain,
        "nameservers": servers,
        "nameservers_on_cloudflare": on_cloudflare,
        "resolves": resolved,
        "human_step_if_not_on_cloudflare": "在 Cloudflare 後台 Add a site 選免費方案，再到註冊商把 nameserver 改成 Cloudflare 給的兩組；生效後由 Agent 繼續",
        "contains_credentials": False,
    }


def command_domain_plan(project: Path, domain: str, *, include_www: bool) -> dict[str, Any]:
    wrangler = read_wrangler_config(project)
    site = read_site_config(project)
    if not DOMAIN_PATTERN.fullmatch(domain):
        raise DeployError("網域格式不正確")
    patterns = [domain] + ([f"www.{domain}"] if include_www else [])
    return {
        "result": "domain_plan",
        "worker_name": wrangler["name"],
        "routes_to_add": [{"pattern": pattern, "custom_domain": True} for pattern in patterns],
        "site_url_change": {"from": site["url"], "to": f"https://{domain}"},
        "redirects_file": f"https://www.{domain}/* https://{domain}/:splat 301" if include_www else None,
        "prerequisites": ["網域已是帳號內啟用的 Cloudflare zone", "該主機名沒有既有的 CNAME 記錄"],
        "effects": ["部署時 Cloudflare 對每個 pattern 自動建立 DNS 記錄與憑證", "根網域與 www 各自綁定，兩邊都能開；_redirects 的 www 轉址是盡力而為，不生效時 www 仍可瀏覽，後台轉址規則屬可選人類步驟", "網站對外以正式網域公開；robots 仍維持目前的 indexing 設定"],
        "human_steps_remaining": ["授權綁定自訂網域"],
        "next": "domain apply --confirm-write，然後 npm run build、deploy --confirm-deploy、verify --url https://" + domain,
        "contains_credentials": False,
    }


def command_domain_apply(project: Path, domain: str, *, include_www: bool, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise DeployError("缺少 --confirm-write；未修改任何檔案")
    plan = command_domain_plan(project, domain, include_www=include_www)
    config = read_wrangler_config(project)
    existing = [route for route in config.get("routes", []) if isinstance(route, dict)]
    patterns = {route.get("pattern") for route in existing}
    for route in plan["routes_to_add"]:
        if route["pattern"] not in patterns:
            existing.append(route)
    config["routes"] = existing
    write_wrangler_config(project, config)
    set_site_field(project, "url", f"https://{domain}")
    redirects_path = project / "public" / "_redirects"
    if include_www:
        redirects_path.parent.mkdir(parents=True, exist_ok=True)
        redirects_path.write_text(plan["redirects_file"] + "\n", encoding="utf-8")
    return {
        "result": "domain_applied",
        "routes": config["routes"],
        "site_url": f"https://{domain}",
        "redirects_file": str(redirects_path) if include_www else None,
        "next": ["npm run build", "deploy --confirm-deploy --expect-indexing " + read_site_config(project)["indexing"], f"verify --url https://{domain} --expect-indexing " + read_site_config(project)["indexing"]],
        "config_patch": {"hosting": {"custom_domain": {"domain": domain}}},
        "contains_credentials": False,
    }


def command_publish(project: Path, *, confirmed: bool) -> dict[str, Any]:
    """把 site.indexing 改為 index。之後必須重建、重部署並讀回。"""

    if not confirmed:
        raise DeployError("缺少 --confirm-write；未修改任何檔案")
    site = read_site_config(project)
    if site["url"].startswith("https://example.invalid"):
        raise DeployError("site.url 仍是 example.invalid；請先用 domain apply 或 set-url 設定正式網址再公開")
    if site["indexing"] == "index":
        return {"result": "already_index", "contains_credentials": False}
    set_site_field(project, "indexing", "index")
    return {
        "result": "indexing_set_to_index",
        "next": ["npm run build", "deploy --confirm-deploy --expect-indexing index", f"verify --url {site['url']} --expect-indexing index"],
        "config_patch": {"verification": {"public_index": "index_authorized"}},
        "contains_credentials": False,
    }


def command_set_url(project: Path, url: str, *, confirmed: bool) -> dict[str, Any]:
    """把 site.url 設成實際的 workers.dev 網址，讓 canonical 與 OG 指到對外可用的位置。"""

    if not confirmed:
        raise DeployError("缺少 --confirm-write；未修改任何檔案")
    if not re.fullmatch(r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,63}", url):
        raise DeployError("網址必須是 https:// 開頭的主機名稱，不含路徑")
    set_site_field(project, "url", url)
    return {"result": "site_url_set", "site_url": url, "next": ["npm run build", "deploy --confirm-deploy --expect-indexing noindex", f"verify --url {url}"], "contains_credentials": False}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="官網部署工具（Cloudflare Workers 靜態資產）")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status"); status.add_argument("--project", required=True)

    plan = sub.add_parser("plan"); plan.add_argument("--project", required=True); plan.add_argument("--config", default=None)
    plan.add_argument("--stage", choices=("workers_dev", "custom_domain", "publish"), default="workers_dev")

    deploy = sub.add_parser("deploy"); deploy.add_argument("--project", required=True)
    deploy.add_argument("--confirm-deploy", action="store_true"); deploy.add_argument("--expect-indexing", choices=("noindex", "index"), default="noindex")

    verify = sub.add_parser("verify"); verify.add_argument("--url", required=True); verify.add_argument("--expect-indexing", choices=("noindex", "index"), default="noindex")

    set_url = sub.add_parser("set-url"); set_url.add_argument("--project", required=True); set_url.add_argument("--url", required=True); set_url.add_argument("--confirm-write", action="store_true")

    domain = sub.add_parser("domain"); domain_sub = domain.add_subparsers(dest="domain_command", required=True)
    check = domain_sub.add_parser("check"); check.add_argument("--domain", required=True)
    dplan = domain_sub.add_parser("plan"); dplan.add_argument("--project", required=True); dplan.add_argument("--domain", required=True); dplan.add_argument("--no-www", action="store_true")
    dapply = domain_sub.add_parser("apply"); dapply.add_argument("--project", required=True); dapply.add_argument("--domain", required=True); dapply.add_argument("--no-www", action="store_true"); dapply.add_argument("--confirm-write", action="store_true")

    publish = sub.add_parser("publish"); publish.add_argument("--project", required=True); publish.add_argument("--confirm-write", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "status":
            result = command_status(validate_project(args.project))
        elif args.command == "plan":
            result = command_plan(validate_project(args.project), load_config(Path(args.config).expanduser() if args.config else None), args.stage)
        elif args.command == "deploy":
            result = command_deploy(validate_project(args.project), confirmed=args.confirm_deploy, expect_indexing=args.expect_indexing)
        elif args.command == "verify":
            result = command_verify(args.url, expect_indexing=args.expect_indexing)
        elif args.command == "set-url":
            result = command_set_url(validate_project(args.project), args.url, confirmed=args.confirm_write)
        elif args.command == "domain":
            if args.domain_command == "check":
                result = command_domain_check(args.domain.lower())
            elif args.domain_command == "plan":
                result = command_domain_plan(validate_project(args.project), args.domain.lower(), include_www=not args.no_www)
            else:
                result = command_domain_apply(validate_project(args.project), args.domain.lower(), include_www=not args.no_www, confirmed=args.confirm_write)
        elif args.command == "publish":
            result = command_publish(validate_project(args.project), confirmed=args.confirm_write)
        else:
            raise DeployError("未知命令")
    except (DeployError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result.get("result") in ("failed", "login_required"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
