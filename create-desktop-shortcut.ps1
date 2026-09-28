$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Bat = Join-Path $Root "start-local.bat"
$Desk = [Environment]::GetFolderPath("Desktop")
$Names = @("video-download-local.lnk", "视频下载-本地.lnk")

$Wsh = New-Object -ComObject WScript.Shell
foreach ($name in $Names) {
    $Lnk = Join-Path $Desk $name
    $Sc = $Wsh.CreateShortcut($Lnk)
    $Sc.TargetPath = $Bat
    $Sc.WorkingDirectory = $Root
    $Sc.IconLocation = "shell32.dll,13"
    $Sc.Description = "启动本地万能视频下载"
    $Sc.Save()
    Write-Host "已创建：$Lnk" -ForegroundColor Green
}

Start-Process explorer.exe -ArgumentList $Desk
