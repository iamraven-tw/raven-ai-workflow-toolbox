"""測試替身：以 JSON 檔模擬 LanceDB 的 connect／open_table／search，只實作本地 RAG 腳本用到的介面。

每個資料表存成 <db>/<名稱>.json，內容為 {"rows": [...], "fts": bool}；
全文檢索只有在 create_index 之後才能使用，否則丟出例外，與真實行為一致。
"""

import json
import math
import re
from pathlib import Path


class _Query:
    def __init__(self, table, query, query_type) -> None:
        self.table, self.query, self.query_type, self.count, self.columns = table, query, query_type, 10, None

    def limit(self, count):
        self.count = count
        return self

    def select(self, columns):
        self.columns = columns
        return self

    def to_list(self):
        rows = self.table._load()["rows"]
        if self.query_type == "fts":
            if not self.table._load()["fts"]:
                raise RuntimeError("Cannot perform full text search unless an INVERTED index has been created")
            terms = set(self.query.split())
            scored = [dict(row, _score=float(len(terms & set(row["text_tok"].split())))) for row in rows]
            scored = [row for row in scored if row["_score"] > 0]
            scored.sort(key=lambda row: -row["_score"])
        else:
            scored = [dict(row, _distance=math.dist(row["vector"], self.query)) for row in rows]
            scored.sort(key=lambda row: row["_distance"])
        keep = set(self.columns or scored[0].keys() if scored else [])
        return [{key: value for key, value in row.items() if key in keep} for row in scored[: self.count]]


class Table:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def add(self, rows) -> None:
        data = self._load()
        data["rows"].extend(rows)
        self._save(data)

    def delete(self, where: str) -> None:
        match = re.fullmatch(r"source = '((?:[^']|'')*)'", where)
        if not match:
            raise ValueError(f"替身只支援 source = '...'：{where}")
        source = match.group(1).replace("''", "'")
        data = self._load()
        data["rows"] = [row for row in data["rows"] if row["source"] != source]
        self._save(data)

    def create_index(self, column, config=None, replace=False) -> None:
        data = self._load()
        data["fts"] = True
        self._save(data)

    def count_rows(self) -> int:
        return len(self._load()["rows"])

    def search(self, query, query_type=None, fts_columns=None):
        return _Query(self, query, query_type)


class _DB:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def list_tables(self):
        if not self.path.is_dir():
            return []
        return sorted(item.stem for item in self.path.glob("*.json"))

    def open_table(self, name):
        table_path = self.path / f"{name}.json"
        if not table_path.is_file():
            raise ValueError(f"Table '{name}' was not found")
        return Table(table_path)

    def create_table(self, name, rows):
        self.path.mkdir(parents=True, exist_ok=True)
        table = Table(self.path / f"{name}.json")
        table._save({"rows": list(rows), "fts": False})
        return table


def connect(path):
    return _DB(path)
