# 本地 RAG 共用工具：連線本機 Ollama 產生向量、jieba 中文斷詞、讀取 PDF／Markdown／純文字／HTML、依標題與段落切成約 700 字的片段。
# 預設把本檔所在位置往上兩層（sources/）當成知識庫根目錄；Ollama 位址、模型與閒置卸載時間可用環境變數覆寫。
"""Shared helpers for the local RAG fallback (Ollama + LanceDB)."""
import os
os.environ.setdefault("RUST_LOG", "error")
import re
from html.parser import HTMLParser
from pathlib import Path
import requests
import jieba
jieba.setLogLevel(60)


def ollama_base(value=None):
    """Ollama 官方的 OLLAMA_HOST 可以不帶 http://（例如 127.0.0.1:11434 或 0.0.0.0），這裡補成可連線的網址。"""
    host = (value or "").strip() or "127.0.0.1:11434"
    if "://" not in host:
        host = "http://" + host
    scheme, rest = host.split("://", 1)
    rest = rest.rstrip("/")
    if rest.startswith("0.0.0.0"):  # 0.0.0.0 是「監聽所有介面」，連線時改用本機
        rest = "127.0.0.1" + rest[len("0.0.0.0"):]
    if not re.search(r":\d+$", rest.split("/", 1)[0]):  # 沒寫連接埠時用 Ollama 預設的 11434
        head, _, tail = rest.partition("/")
        rest = head + ":11434" + ("/" + tail if tail else "")
    return f"{scheme}://{rest}"


OLLAMA = ollama_base(os.environ.get("OLLAMA_HOST"))
MODEL = os.environ.get("RAG_EMBED_MODEL", "qwen3-embedding:4b")
KEEP_ALIVE = os.environ.get("RAG_KEEP_ALIVE", "2m")
QUERY_INSTRUCT = "Instruct: Given a search query, retrieve relevant passages that answer the query\nQuery: "
# 只接受這些副檔名；其他格式（Word、簡報、圖片、壓縮檔等）一律列為 unsupported 並留在收件匣
SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf", ".html", ".htm"}


class UnreadableFile(Exception):
    """檔案格式支援但內容無法正確讀取（例如不是 UTF-8 編碼）。"""


def root(arg=None):
    return Path(arg) if arg else Path(__file__).resolve().parents[2]  # .../sources

def db_path(r): return r / "rag" / "lancedb"

def table_names(db):
    res = db.list_tables()
    return list(getattr(res, "tables", res))

def embed(texts, batch=16):
    out = []
    for i in range(0, len(texts), batch):
        r = requests.post(f"{OLLAMA}/api/embed", json={"model": MODEL, "input": texts[i:i+batch], "keep_alive": KEEP_ALIVE}, timeout=600)
        r.raise_for_status(); out += r.json()["embeddings"]
    return out

def tok(text):
    """Chinese word segmentation so LanceDB whitespace full-text search works."""
    return " ".join(w for w in jieba.cut_for_search(text.lower()) if w.strip())

def is_supported(p: Path):
    return p.suffix.lower() in SUPPORTED_SUFFIXES


class _HTMLText(HTMLParser):
    """從 HTML 取出可讀文字，略過 script／style，區塊元素之間換段。"""
    BLOCKS = {"p", "div", "br", "li", "tr", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(); self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1
        elif tag in ("h1", "h2", "h3", "h4"): self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in self.BLOCKS: self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip: self.skip -= 1
        elif tag in self.BLOCKS: self.parts.append("\n\n")

    def handle_data(self, data):
        if not self.skip: self.parts.append(data)


def read_text(p: Path):
    """讀取支援的檔案；格式不支援、不是 UTF-8 或看起來是二進位檔時丟出例外，不用亂碼建立索引。"""
    suffix = p.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnreadableFile(f"不支援的格式：{suffix or '（沒有副檔名）'}")
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n\n".join(f"<!-- page {i+1} -->\n" + (pg.extract_text() or "") for i, pg in enumerate(PdfReader(str(p)).pages))
    data = p.read_bytes()
    if b"\x00" in data:
        raise UnreadableFile("內容含有二進位資料，不是純文字檔")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise UnreadableFile("不是 UTF-8 編碼（可能是 Big5），請先另存成 UTF-8 再匯入") from e
    if suffix in (".html", ".htm"):
        parser = _HTMLText(); parser.feed(text); parser.close()
        text = re.sub(r"[ \t]+", " ", "".join(parser.parts))
        text = re.sub(r"\n\s*\n\s*", "\n\n", text).strip()
    return text

PAGE_MARKER = re.compile(r"<!--\s*page\s+(\d+)\s*-->")

def chunk(text, size=700, overlap=120):
    """先依 PDF 頁碼標記與 Markdown 標題分段，再依段落切成約 size 字的片段；回傳 (section, text)。
    section 是最近的標題；PDF 是「第 N 頁」，頁內有標題時是「第 N 頁｜標題」；兩者都沒有時是「（開頭）」。
    頁碼標記只用來決定 section，不留在片段文字裡。"""
    chunks, page, heading, buf = [], None, None, ""
    def section():
        if page is None:
            return heading or "（開頭）"
        return f"第 {page} 頁｜{heading}" if heading else f"第 {page} 頁"
    def flush():
        nonlocal buf
        t = buf.strip()
        while len(t) > size:
            chunks.append((section(), t[:size])); t = t[size-overlap:]
        if t: chunks.append((section(), t))
        buf = ""
    # re.split 帶群組時回傳 [標記前文字, 頁碼, 該頁文字, 頁碼, 該頁文字, …]
    parts = PAGE_MARKER.split(text)
    for index in range(0, len(parts), 2):
        if index:
            flush(); page = int(parts[index - 1])
        for para in re.split(r"\n\s*\n", parts[index]):
            m = re.match(r"^(#{1,4})\s+(.+)", para.strip())
            if m:
                flush(); heading = m.group(2).strip()[:120]
                rest = para.strip().split("\n", 1)
                para = rest[1] if len(rest) > 1 else ""
            if len(buf) + len(para) > size: flush()
            buf += para + "\n\n"
    flush()
    return chunks
