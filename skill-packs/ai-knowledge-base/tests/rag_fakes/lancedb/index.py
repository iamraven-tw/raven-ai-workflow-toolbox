"""測試替身：FTS 設定只記錄參數。"""


class FTS:
    def __init__(self, **options) -> None:
        self.options = options
