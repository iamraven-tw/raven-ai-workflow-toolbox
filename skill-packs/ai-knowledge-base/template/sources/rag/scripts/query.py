# 混合檢索：向量相似度加上中文全文檢索，以倒數排名合併，輸出含檔案與段落標題的 JSON。
# Qwen3 Embedding 需要的查詢前綴已在本檔自動加上，Agent 直接傳入使用者的問題即可。
# 還沒有索引時印出 {"error": "no_index", ...} 並以結束碼 1 結束；全文索引不可用時，fts 模式同樣回報錯誤，hybrid 模式改用向量結果並在 stderr 警告。
"""Hybrid search (vector + Chinese full-text, merged by reciprocal rank). Prints JSON hits with file + section.
On failure prints {"error": <code>, "message": ...} and exits 1.
Usage: query.py "問題" [-k 5] [--mode hybrid|vector|fts] [--root DIR]"""
import argparse, json, sys
from common import *
import lancedb


def fail(code, message):
    print(json.dumps({"error": code, "message": message}, ensure_ascii=False)); sys.exit(1)


ap = argparse.ArgumentParser(); ap.add_argument("q"); ap.add_argument("-k", type=int, default=5)
ap.add_argument("--mode", default="hybrid", choices=["hybrid", "vector", "fts"]); ap.add_argument("--root"); a = ap.parse_args()
db = lancedb.connect(str(db_path(root(a.root))))
if "chunks" not in table_names(db):
    fail("no_index", "本地 RAG 目前沒有資料：還沒有匯入任何外部原文")
tb = db.open_table("chunks")
cols = ["source", "section", "chunk", "text"]; lists = []
if a.mode in ("hybrid", "vector"):
    try: v = embed([QUERY_INSTRUCT + a.q])[0]
    except Exception as e: fail("embed_failed", f"無法向 Ollama 取得查詢向量：{type(e).__name__}: {e}")
    lists.append(tb.search(v).limit(a.k*4).select(cols + ["_distance"]).to_list())
if a.mode in ("hybrid", "fts"):
    try: lists.append(tb.search(tok(a.q), query_type="fts", fts_columns="text_tok").limit(a.k*4).select(cols + ["_score"]).to_list())
    except Exception as e:
        if a.mode == "fts": fail("fts_unavailable", f"全文索引無法使用，請重新匯入以重建：{type(e).__name__}: {e}")
        print(f"警告：全文索引無法使用，只用向量結果（{type(e).__name__}）", file=sys.stderr)
score, rows = {}, {}
for L in lists:
    for rank, r in enumerate(L):
        key = (r["source"], r["chunk"]); rows[key] = r
        score[key] = score.get(key, 0) + 1/(60 + rank)
top = sorted(score, key=score.get, reverse=True)[:a.k]
print(json.dumps([{"source": rows[k]["source"], "section": rows[k]["section"], "chunk": rows[k]["chunk"], "score": round(score[k], 4), "text": rows[k]["text"]} for k in top], ensure_ascii=False, indent=1))
