"""測試替身：以空白與標點切詞，並把連續中文拆成單字與雙字詞，近似 jieba.cut_for_search。"""

import re


def setLogLevel(level):  # noqa: N802（沿用 jieba 的函式名稱）
    """真實 jieba 用來關閉日誌；替身不需要做事。"""


def cut_for_search(text):
    for token in re.findall(r"[a-z0-9]+|[一-鿿]+", text):
        if re.match(r"[a-z0-9]", token):
            yield token
            continue
        yield from token
        for index in range(len(token) - 1):
            yield token[index:index + 2]
