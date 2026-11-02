#!/usr/bin/env python3
"""本地 RAG 測試：用假的 Ollama 服務與虛構文件，驗證收件匣分流、格式限制、索引、重建與查詢。

分成兩組：

1. 確定性測試（預設執行）：以 `tests/rag_fakes/` 的替身取代 requests、jieba、lancedb 與 pypdf，
   不需要安裝任何套件，`python3 -m unittest discover -s tests -p 'test_*.py'` 就會跑。
2. 真實套件端對端測試（選用）：需要一個已安裝 lancedb、pyarrow、jieba、pypdf、requests 的 Python：

       AI_KB_RAG_PYTHON=<該 Python 路徑> python3 -m unittest discover -s tests -p 'test_*.py'

   沒有設定時這組略過；兩組都不代表 Ollama 或真實向量模型已測試。
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SOURCES = PACKAGE_ROOT / "template" / "sources"
SCRIPTS = TEMPLATE_SOURCES / "rag" / "scripts"
FAKES = Path(__file__).resolve().parent / "rag_fakes"
RAG_PYTHON = os.environ.get("AI_KB_RAG_PYTHON", "")


def fake_vector(text: str) -> list[float]:
    """以字元雜湊產生固定維度的假向量，讓相同字詞的文字彼此相近。"""

    # 模擬向量模型理解 Instruct 前綴：只用「Query: 」之後的文字計算
    text = text.split("Query: ", 1)[-1]
    vector = [0.0] * 256
    for character in text:
        vector[int(hashlib.md5(character.encode()).hexdigest(), 16) % 256] += 1
    norm = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / norm for value in vector]


class FakeOllama(BaseHTTPRequestHandler):
    """只實作 /api/embed，並記錄收到的輸入以檢查查詢前綴。"""

    received: list[str] = []

    def do_POST(self) -> None:  # noqa: N802（http.server 規定的方法名稱）
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOllama.received.extend(body["input"])
        payload = json.dumps({"embeddings": [fake_vector(text) for text in body["input"]]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        """測試時不輸出存取紀錄。"""


def closed_port() -> int:
    """取得一個目前沒有服務在聽的本機連接埠，模擬 Ollama 沒有啟動。"""

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def topic_document(title: str, sections: dict[str, str]) -> str:
    """組出有標題與段落的虛構 Markdown。"""

    return f"# {title}\n\n" + "\n\n".join(f"## {name}\n\n{body}" for name, body in sections.items())


PRICING = topic_document(
    "虛構工作室定價手冊",
    {
        "退款政策": "購買後七天鑑賞期內可以全額退款，退款在五個工作天內退回原付款方式。",
        "訂閱方案": "月費方案每月扣款，年費方案一次付清並享有兩個月折扣。",
        "團體報名": "五人以上團體報名可享九折優惠，需要由同一位聯絡人統一付款。",
    },
)
GARDEN = topic_document(
    "虛構社區花園手冊",
    {
        "澆水排程": "夏季清晨澆水，冬季每三天澆一次，雨天暫停自動灑水器。",
        "堆肥規則": "落葉與果皮放進綠色桶，肉類與油脂不得放入堆肥區。",
    },
)
def minimal_pdf(*pages: str) -> bytes:
    """手寫一份每頁一行英文文字的最小 PDF（含正確的 xref），用來驗證 pypdf 讀取與頁碼段落。"""

    count = len(pages)
    kids = " ".join(f"{3 + 2 * index} 0 R" for index in range(count))
    font = 3 + 2 * count
    objects = [b"<</Type/Catalog/Pages 2 0 R>>", f"<</Type/Pages/Kids[{kids}]/Count {count}>>".encode()]
    for index, text in enumerate(pages):
        stream = f"BT /F1 18 Tf 20 60 Td ({text}) Tj ET".encode()
        objects.append(
            f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents {4 + 2 * index} 0 R"
            f"/Resources<</Font<</F1 {font} 0 R>>>>>>".encode()
        )
        objects.append(b"<</Length %d>>stream\n" % len(stream) + stream + b"\nendstream")
    objects.append(b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")
    output, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(output)
    output += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    output += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    output += b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(output)


class LocalRagScenarios:
    """兩組測試共用的情境；子類別決定使用哪個 Python 與是否套用替身。"""

    python = ""
    extra_pythonpath = ""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ai-kb-rag-test-")
        self.sources = Path(self.temporary.name) / "sources"
        shutil.copytree(TEMPLATE_SOURCES, self.sources, ignore=shutil.ignore_patterns("__pycache__"))
        self.inbox = self.sources / "inbox"
        self.server = HTTPServer(("127.0.0.1", 0), FakeOllama)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        # 刻意使用 Ollama 官方格式（不含 http://），同時驗證位址補全
        self.env = dict(os.environ, OLLAMA_HOST=f"127.0.0.1:{self.server.server_port}")
        if self.extra_pythonpath:
            self.env["PYTHONPATH"] = self.extra_pythonpath
        else:
            self.env.pop("PYTHONPATH", None)
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        FakeOllama.received = []

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.temporary.cleanup()

    def run_script(self, name: str, *arguments: str, expect_code: int = 0, env: dict | None = None) -> object:
        """以指定 Python 從暫存目錄外執行工作區內的腳本並解析 JSON 輸出。"""

        result = subprocess.run(
            [self.python, "-W", "ignore", str(self.sources / "rag" / "scripts" / name), *arguments],
            capture_output=True,
            text=True,
            env=env or self.env,
            cwd=Path(self.temporary.name).parent,
        )
        self.assertEqual(result.returncode, expect_code, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def inbox_names(self) -> list[str]:
        return sorted(path.name for path in self.inbox.iterdir() if not path.name.startswith("."))

    def external_names(self) -> list[str]:
        return sorted(path.name for path in (self.sources / "external").iterdir())

    def stub_names(self) -> list[str]:
        return sorted(path.name for path in (self.sources / "wiki").glob("ext_*.md"))

    def test_default_threshold_splits_long_and_short(self) -> None:
        long_text = PRICING + "\n\n## 附錄\n\n" + "虛構說明文字。" * 900
        (self.inbox / "pricing-report.md").write_text(long_text, encoding="utf-8")
        (self.inbox / "my-note.md").write_text("虛構短筆記：定價先問客戶。", encoding="utf-8")

        report = self.run_script("ingest.py")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["unsupported"], [])
        self.assertEqual([item["file"] for item in report["external"]], ["external/pricing-report.md"])
        self.assertFalse(report["external"][0]["reindexed"])
        self.assertEqual(report["wiki_pending"], [str(self.inbox / "my-note.md")])
        self.assertEqual(self.inbox_names(), ["my-note.md"])
        self.assertIn("pricing-report.md", self.external_names())
        self.assertTrue((self.sources / "rag" / "lancedb").is_dir())
        stub = (self.sources / "wiki" / "ext_pricing-report.md").read_text(encoding="utf-8")
        self.assertIn("source: external/pricing-report.md", stub)
        self.assertIn("](../external/pricing-report.md)", stub)

    def test_query_returns_matching_section_in_every_mode(self) -> None:
        (self.inbox / "pricing.md").write_text(PRICING, encoding="utf-8")
        (self.inbox / "garden.md").write_text(GARDEN, encoding="utf-8")
        report = self.run_script("ingest.py", "--min-chars", "50")
        self.assertEqual(sorted(item["file"] for item in report["external"]), ["external/garden.md", "external/pricing.md"])

        for mode in ("hybrid", "vector", "fts"):
            with self.subTest(mode=mode):
                hits = self.run_script("query.py", "七天鑑賞期退款", "-k", "3", "--mode", mode)
                self.assertTrue(hits)
                self.assertEqual(hits[0]["source"], "external/pricing.md")
                self.assertEqual(hits[0]["section"], "退款政策")
                self.assertIn("鑑賞期", hits[0]["text"])
        hits = self.run_script("query.py", "冬季澆水", "-k", "1", "--mode", "fts")
        self.assertEqual((hits[0]["source"], hits[0]["section"]), ("external/garden.md", "澆水排程"))
        self.assertTrue(any(text.startswith("Instruct:") for text in FakeOllama.received))

    def test_unsupported_and_unreadable_files_stay_in_inbox(self) -> None:
        random_bytes = random.Random(7).randbytes(9000)
        (self.inbox / "image.png").write_bytes(random_bytes)
        (self.inbox / "slides.pptx").write_bytes(b"PK\x03\x04" + random_bytes)
        (self.inbox / "folder").mkdir()
        (self.inbox / "folder" / "inside.md").write_text(PRICING, encoding="utf-8")
        (self.inbox / "big5-report.txt").write_bytes(("虛構的繁體中文報告內容。" * 800).encode("big5"))
        (self.inbox / "binary.md").write_bytes(b"\x00\x01" + random_bytes)

        report = self.run_script("ingest.py", "--all-external")
        unsupported = {Path(item["file"]).name for item in report["unsupported"]}
        self.assertEqual(unsupported, {"image.png", "slides.pptx", "folder"})
        errors = {Path(item["file"]).name: item["error"] for item in report["errors"]}
        self.assertEqual(set(errors), {"big5-report.txt", "binary.md"})
        self.assertIn("UTF-8", errors["big5-report.txt"])
        self.assertEqual(report["external"], [])
        self.assertEqual(report["wiki_pending"], [])
        self.assertEqual(self.inbox_names(), ["big5-report.txt", "binary.md", "folder", "image.png", "slides.pptx"])
        self.assertEqual(self.external_names(), ["README.md"])
        self.assertEqual(self.stub_names(), [])

    def test_ollama_down_keeps_file_in_inbox(self) -> None:
        (self.inbox / "pricing.md").write_text(PRICING, encoding="utf-8")
        env = dict(self.env, OLLAMA_HOST=f"http://127.0.0.1:{closed_port()}")
        report = self.run_script("ingest.py", "--min-chars", "50", env=env)
        self.assertEqual([Path(item["file"]).name for item in report["errors"]], ["pricing.md"])
        self.assertEqual(report["external"], [])
        self.assertEqual(self.inbox_names(), ["pricing.md"])
        self.assertEqual(self.external_names(), ["README.md"])
        self.assertEqual(self.stub_names(), [])

    def test_rebuild_from_external_does_not_duplicate(self) -> None:
        (self.inbox / "pricing.md").write_text(PRICING, encoding="utf-8")
        (self.inbox / "garden.md").write_text(GARDEN, encoding="utf-8")
        first = self.run_script("ingest.py", "--min-chars", "50")
        self.assertEqual(len(first["external"]), 2)
        stub = self.sources / "wiki" / "ext_pricing.md"
        stub.write_text(stub.read_text(encoding="utf-8") + "\n使用者補寫的摘要。\n", encoding="utf-8")
        before = (self.external_names(), self.stub_names(), stub.read_text(encoding="utf-8"))
        hits_before = self.run_script("query.py", "七天鑑賞期退款", "-k", "20", "--mode", "fts")

        # 依文件的重建流程：刪除索引，把 external/ 的檔案（文件說不含 README.md，這裡故意一起複製）複製回收件匣
        shutil.rmtree(self.sources / "rag" / "lancedb")
        for path in (self.sources / "external").iterdir():
            shutil.copy2(path, self.inbox / path.name)
        # 預設門檻下這兩份都是短文，仍要以原路徑重新索引，而不是落入 wiki_pending
        second = self.run_script("ingest.py")
        self.assertEqual(sorted(item["file"] for item in second["external"]), ["external/garden.md", "external/pricing.md"])
        self.assertTrue(all(item["reindexed"] for item in second["external"]))
        self.assertEqual(second["wiki_pending"], [])
        self.assertEqual([Path(item["file"]).name for item in second["unsupported"]], ["README.md"])
        self.assertEqual((self.external_names(), self.stub_names(), stub.read_text(encoding="utf-8")), before)
        self.assertEqual(self.inbox_names(), ["README.md"])

        # 索引還在時再匯入一次相同檔案，也不得出現重複片段
        shutil.copy2(self.sources / "external" / "pricing.md", self.inbox / "pricing.md")
        third = self.run_script("ingest.py")
        self.assertEqual([item["file"] for item in third["external"]], ["external/pricing.md"])
        hits_after = self.run_script("query.py", "七天鑑賞期退款", "-k", "20", "--mode", "fts")
        self.assertEqual(
            sorted((hit["source"], hit["chunk"]) for hit in hits_after),
            sorted((hit["source"], hit["chunk"]) for hit in hits_before),
        )
        self.assertEqual(self.external_names(), before[0])

    def test_changed_same_name_file_gets_suffixed_copy(self) -> None:
        (self.inbox / "pricing.md").write_text(PRICING, encoding="utf-8")
        self.run_script("ingest.py", "--min-chars", "50")
        updated = PRICING.replace("七天", "十天")
        (self.inbox / "pricing.md").write_text(updated, encoding="utf-8")
        report = self.run_script("ingest.py", "--min-chars", "50")
        suffix = hashlib.md5(updated.encode()).hexdigest()[:6]
        self.assertEqual([item["file"] for item in report["external"]], [f"external/pricing-{suffix}.md"])
        self.assertFalse(report["external"][0]["reindexed"])
        self.assertEqual(self.stub_names(), sorted(["ext_pricing.md", f"ext_pricing-{suffix}.md"]))

    def test_filename_with_space_gets_valid_link_and_frontmatter(self) -> None:
        (self.inbox / "my report: v2.md").write_text(PRICING, encoding="utf-8")
        report = self.run_script("ingest.py", "--min-chars", "50")
        self.assertEqual(report["errors"], [])
        stub = (self.sources / "wiki" / "ext_my report: v2.md").read_text(encoding="utf-8")
        self.assertIn('source: "external/my report: v2.md"', stub)
        self.assertIn("](<../external/my report: v2.md>)", stub)

    def test_pdf_chunks_carry_page_sections(self) -> None:
        (self.inbox / "refund.pdf").write_bytes(minimal_pdf("Fictional refund policy", "Fictional shipping rules"))
        report = self.run_script("ingest.py")
        self.assertEqual(report["errors"], [])
        self.assertEqual([item["file"] for item in report["external"]], ["external/refund.pdf"])
        hits = self.run_script("query.py", "refund policy", "-k", "5")
        sections = {hit["section"]: hit["text"] for hit in hits if hit["source"] == "external/refund.pdf"}
        self.assertEqual(sorted(sections), ["第 1 頁", "第 2 頁"])
        self.assertIn("refund", sections["第 1 頁"].lower())
        self.assertIn("shipping", sections["第 2 頁"].lower())
        self.assertTrue(all("<!--" not in text for text in sections.values()))

    def test_query_without_index_prints_short_json_error(self) -> None:
        result = self.run_script("query.py", "任何問題", expect_code=1)
        self.assertEqual(result["error"], "no_index")
        self.assertIn("沒有資料", result["message"])


class LocalRagDeterministicTest(LocalRagScenarios, unittest.TestCase):
    """用替身套件執行腳本，預設就會跑，不需要網路或任何第三方套件。"""

    python = sys.executable
    extra_pythonpath = str(FAKES)


@unittest.skipUnless(RAG_PYTHON, "未設定 AI_KB_RAG_PYTHON，略過真實套件的本地 RAG 端對端測試")
class LocalRagEndToEndTest(LocalRagScenarios, unittest.TestCase):
    """以真實的 lancedb、pyarrow、jieba、pypdf、requests 執行同一組情境。"""

    python = RAG_PYTHON


class CommonHelpersTest(unittest.TestCase):
    """直接匯入 common.py（套用替身），測試位址補全、格式限制、編碼與切段。"""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path[:0] = [str(FAKES), str(SCRIPTS)]
        # 不在範本裡留下 __pycache__，以免安裝時被複製進使用者工作區
        cls.previous_bytecode, sys.dont_write_bytecode = sys.dont_write_bytecode, True
        cls.common = importlib.import_module("common")

    @classmethod
    def tearDownClass(cls) -> None:
        for path in (str(FAKES), str(SCRIPTS)):
            sys.path.remove(path)
        for name in ("common", "requests", "jieba", "pypdf"):
            sys.modules.pop(name, None)
        sys.dont_write_bytecode = cls.previous_bytecode

    def test_ollama_host_formats(self) -> None:
        base = self.common.ollama_base
        self.assertEqual(base(None), "http://127.0.0.1:11434")
        self.assertEqual(base("127.0.0.1:5000"), "http://127.0.0.1:5000")
        self.assertEqual(base("0.0.0.0"), "http://127.0.0.1:11434")
        self.assertEqual(base("http://localhost:11434/"), "http://localhost:11434")
        self.assertEqual(base("https://ollama.example.test"), "https://ollama.example.test:11434")

    def test_read_text_rules(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            folder_path = Path(folder)
            (folder_path / "a.docx").write_bytes(b"PK")
            (folder_path / "b.txt").write_bytes("繁體中文".encode("big5"))
            (folder_path / "c.md").write_bytes("﻿# 標題\n\n內容".encode("utf-8"))
            (folder_path / "d.html").write_text(
                "<html><style>x{}</style><body><h2>退款</h2><p>七天內</p><script>bad()</script></body></html>",
                encoding="utf-8",
            )
            with self.assertRaises(self.common.UnreadableFile):
                self.common.read_text(folder_path / "a.docx")
            with self.assertRaises(self.common.UnreadableFile):
                self.common.read_text(folder_path / "b.txt")
            self.assertEqual(self.common.read_text(folder_path / "c.md"), "# 標題\n\n內容")
            html_text = self.common.read_text(folder_path / "d.html")
            self.assertIn("## 退款", html_text)
            self.assertIn("七天內", html_text)
            self.assertNotIn("bad()", html_text)
            self.assertNotIn("x{}", html_text)

    def test_chunk_keeps_sections_and_overlap(self) -> None:
        chunks = self.common.chunk("前言\n\n## 第一節\n\n" + "甲" * 1500 + "\n\n## 第二節\n\n乙")
        self.assertEqual(chunks[0], ("（開頭）", "前言"))
        first = [text for section, text in chunks if section == "第一節"]
        self.assertTrue(all(len(text) <= 700 for text in first))
        self.assertEqual(sum(len(text) for text in first) - 120 * (len(first) - 1), 1500)
        self.assertEqual(chunks[-1], ("第二節", "乙"))

    def test_chunk_uses_pdf_page_markers(self) -> None:
        text = "<!-- page 1 -->\n封面文字\n\n<!-- page 2 -->\n## 退款\n\n七天內\n\n<!-- page 3 -->\n續上頁\n\n<!-- page 4 -->\n"
        self.assertEqual(
            self.common.chunk(text),
            [("第 1 頁", "封面文字"), ("第 2 頁｜退款", "七天內"), ("第 3 頁｜退款", "續上頁")],
        )
        long_page = self.common.chunk("<!-- page 7 -->\n" + "丙" * 1000)
        self.assertGreater(len(long_page), 1)
        self.assertTrue(all(section == "第 7 頁" for section, _ in long_page))


if __name__ == "__main__":
    unittest.main()
