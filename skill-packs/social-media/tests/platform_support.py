"""跨平台測試前提；只調整新建的虛構暫存目錄，不改使用者工作區。"""

import json
import os
from pathlib import Path
import subprocess


def symlink_or_skip(case, link, target, *, directory=False):
    """只略過 Windows 缺少建立 symlink 權限，其他 OS 錯誤不得隱藏。"""
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as error:
        if os.name == "nt" and getattr(error, "winerror", None) == 1314:
            case.skipTest("Windows 未授予 symlink 權限；需在具權限環境補驗")
        raise


def _powershell(path, script):
    """路徑透過環境傳入，不拼接成可執行的命令字串。"""
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
         "$ErrorActionPreference = 'Stop'; "
         "Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1'); "
         + script],
        env=dict(os.environ, FICTIONAL_ACL_PATH=str(path)),
        capture_output=True, text=True, check=True, timeout=30)
    return result.stdout


def private_fixture(root):
    """Windows chmod 不限制讀取；為新建的空測試根明確設定 DACL。"""
    if os.name != "nt":
        return
    if not Path(root).is_dir() or any(Path(root).iterdir()):
        raise ValueError("只可設定新建的空測試目錄")
    _powershell(root, r"""
        $userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $acl = [Security.AccessControl.DirectorySecurity]::new(
            $env:FICTIONAL_ACL_PATH, [Security.AccessControl.AccessControlSections]::Access)
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($oldRule in @($acl.Access)) {
            $acl.RemoveAccessRuleSpecific($oldRule)
        }
        foreach ($sid in @($userSid, 'S-1-5-18', 'S-1-5-32-544')) {
            $identity = [Security.Principal.SecurityIdentifier]::new($sid)
            $rule = [Security.AccessControl.FileSystemAccessRule]::new(
                $identity, 'FullControl', 'ContainerInherit, ObjectInherit', 'None', 'Allow')
            $acl.AddAccessRule($rule)
        }
        [IO.Directory]::SetAccessControl($env:FICTIONAL_ACL_PATH, $acl)
    """)


def assert_private_file(case, path):
    """POSIX 驗證 0600；Windows 驗證產物 DACL 沒有額外允許的主體。"""
    if os.name != "nt":
        case.assertEqual(path.stat().st_mode & 0o777, 0o600)
        return
    result = json.loads(_powershell(path, r"""
        $acl = Get-Acl -LiteralPath $env:FICTIONAL_ACL_PATH
        $allowed = @([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,
                     'S-1-5-18', 'S-1-5-32-544')
        # Python 產物可能使用 OWNER RIGHTS；先核對擁有者才承認此 SID。
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -eq $allowed[0]) {
            $allowed += 'S-1-3-4'
        }
        $rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
        $grants = @($rules | Where-Object { $_.AccessControlType -eq 'Allow' })
        $unexpected = @($grants | Where-Object { $_.IdentityReference.Value -notin $allowed })
        @{ grants = $grants.Count; unexpected = $unexpected.Count } | ConvertTo-Json -Compress
    """))
    case.assertGreater(result["grants"], 0, "不得使用空或無限制 DACL")
    case.assertEqual(result["unexpected"], 0, "產物包含預期以外的 ACL 允許主體")
