# 處理 sources/inbox/：PDF 或 6000 字以上的長文移到 external/、切段寫進 LanceDB，並建立 wiki/ext_*.md 摘要頁草稿；
# 其他短文與自己的筆記只列在 wiki_pending，交給 Agent 依既有規則歸檔。
# 只接受 .md、.markdown、.txt、.pdf、.html、.htm；其他格式與子資料夾列在 unsupported，讀不出正確文字的列在 errors，兩者都留在 inbox/。
# 收件匣裡的檔案若與 external/ 的同名檔內容完全相同（例如重建索引時複製回來），就直接以原路徑重新建索引、刪除收件匣副本，不另存新檔、不重複建立摘要頁。
"""Process sources/inbox/. PDF or >= MIN_CHARS text -> external/ + LanceDB + wiki/ext_*.md stub.
Other supported files are listed as 'wiki_pending'; unsupported types/folders as 'unsupported'.
A file identical to external/<same name> is re-indexed in place ('reindexed': true).
Prints a JSON report. Usage: ingest.py [--root DIR] [--min-chars 6000] [--all-external]"""
import argparse, json, shutil, time, hashlib, datetime, re
from common import *
import lancedb
from lancedb.index import FTS

ap = argparse.ArgumentParser(); ap.add_argument("--root"); ap.add_argument("--min-chars", type=int, default=6000)
ap.add_argument("--all-external", action="store_true"); a = ap.parse_args()
R = root(a.root); inbox, ext, wiki = R/"inbox", R/"external", R/"wiki"
for d in (inbox, ext, wiki): d.mkdir(parents=True, exist_ok=True)
db = lancedb.connect(str(db_path(R)))
report = {"external": [], "wiki_pending": [], "unsupported": [], "errors": []}
today = datetime.date.today().isoformat(); t0 = time.time(); changed = False


def digest(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def link_target(rel):
    """Markdown 連結目標含空白或括號時用 <...> 包起來，否則不是有效的 CommonMark 連結。"""
    target = f"../{rel}"
    return f"<{target}>" if re.search(r"[\s()<>]", target) else target


def yaml_value(value):
    """frontmatter 的值含冒號、井號等特殊字元時加上雙引號。"""
    return json.dumps(value, ensure_ascii=False) if re.search(r"[:#\[\]{}&*!|>'\"%@`,]|^\s|\s$|^-", value) else value


for f in sorted(p for p in inbox.iterdir() if not p.name.startswith(".")):
    if f.is_dir():
        report["unsupported"].append({"file": str(f), "reason": "子資料夾不會處理；請把裡面的檔案直接放進 inbox/"}); continue
    if not f.is_file():
        continue
    if not is_supported(f):
        report["unsupported"].append({"file": str(f), "reason": f"不支援的格式：{f.suffix.lower() or '（沒有副檔名）'}"}); continue
    if f.name == "README.md" and (ext / "README.md").is_file() and digest(f) == digest(ext / "README.md"):
        report["unsupported"].append({"file": str(f), "reason": "這是 external/ 的說明檔，不需要匯入；可刪除收件匣裡的這份副本"}); continue
    try:
        text = read_text(f)
        file_hash = digest(f)
        # 先找 external/ 裡內容完全相同的同名檔（含帶雜湊尾碼的舊版本）
        dest, reindex = None, False
        for candidate in (ext / f.name, ext / f"{f.stem}-{file_hash[:6]}{f.suffix}"):
            if candidate.is_file() and digest(candidate) == file_hash:
                dest, reindex = candidate, True; break
        if not reindex:
            if not (a.all_external or f.suffix.lower() == ".pdf" or len(text) >= a.min_chars):
                report["wiki_pending"].append(str(f)); continue
            dest = ext / f.name
            if dest.exists(): dest = ext / f"{f.stem}-{file_hash[:6]}{f.suffix}"
        rel = dest.relative_to(R).as_posix()
        ch = chunk(text)
        if not ch:
            raise UnreadableFile("讀不到任何文字（可能是沒有文字層的掃描 PDF）")
        vecs = embed([f"{s}\n{t}" for s, t in ch])
        rows = [{"vector": v, "source": rel, "section": s, "chunk": i, "text": t, "text_tok": tok(s + " " + t)} for i, ((s, t), v) in enumerate(zip(ch, vecs))]
        if "chunks" in table_names(db):
            tb = db.open_table("chunks"); tb.delete("source = '" + rel.replace("'", "''") + "'"); tb.add(rows)
        else: db.create_table("chunks", rows)
        changed = True
        if reindex: f.unlink()  # 與 external/ 原檔相同，只是收件匣副本
        else: shutil.move(str(f), dest)
        stub = wiki / f"ext_{dest.stem}.md"
        if not stub.exists():
            stub.write_text(f"---\ntype: topic\nstatus: draft\nsource: {yaml_value(rel)}\nrag: true\nadded: {today}\n---\n\n# {dest.stem}\n\n外部原文，已收進本地 RAG（{len(ch)} 段）。原檔：[{rel}]({link_target(rel)})\n\n## 摘要\n\n（待 Agent 補寫三到五行摘要與關鍵詞）\n", encoding="utf-8")
        report["external"].append({"file": rel, "chunks": len(ch), "chars": len(text), "wiki_stub": stub.relative_to(R).as_posix(), "reindexed": reindex})
    except Exception as e: report["errors"].append({"file": str(f), "error": f"{type(e).__name__}: {e}"})
if changed:
    db.open_table("chunks").create_index("text_tok", config=FTS(base_tokenizer="whitespace", stem=False, remove_stop_words=False, lower_case=True), replace=True)
report["seconds"] = round(time.time() - t0, 1)
print(json.dumps(report, ensure_ascii=False, indent=1))
