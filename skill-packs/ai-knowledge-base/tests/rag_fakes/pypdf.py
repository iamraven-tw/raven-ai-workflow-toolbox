"""測試替身：只讀 test_local_rag.minimal_pdf 產生的極簡 PDF，每個 `(文字) Tj` 內容串流視為一頁。"""

import re


class _Page:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class PdfReader:
    """模仿 pypdf.PdfReader 的 pages 介面；依物件順序取出每頁的文字。"""

    def __init__(self, path):
        data = open(path, "rb").read().decode("latin-1")
        self.pages = [_Page(text) for text in re.findall(r"\((.*?)\) Tj", data)]
