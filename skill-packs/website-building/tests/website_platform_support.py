"""Windows 一般帳號的 symlink 測試前置條件。"""

import os


def directory_symlink_or_skip(case, target, link):
    """只略過 WinError 1314，不能吞掉其他 I/O 或防護錯誤。"""
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as error:
        if os.name == "nt" and getattr(error, "winerror", None) == 1314:
            case.skipTest("Windows 未授予 symlink 權限；需在具權限環境補驗")
        raise
