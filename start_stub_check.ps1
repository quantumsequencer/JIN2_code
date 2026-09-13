$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$source = Join-Path $workspace 'SGMO2_original/JinGateway-0.2.0.09030'
$target = Join-Path $PSScriptRoot '.stub_gateway'
if (Test-Path (Join-Path $target 'check.pid')) {
    $previousId = [int](Get-Content (Join-Path $target 'check.pid'))
    if (Get-Process -Id $previousId -ErrorAction SilentlyContinue) {
        throw 'The previous isolated Stub check is still running.'
    }
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
foreach ($name in @('JinGateway.exe','JinGateway.exe.config','resources.json')) {
    Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $target $name)
}
Copy-Item -LiteralPath (Join-Path $source 'dlls') -Destination $target -Recurse -Force
$config = Get-Content (Join-Path $source 'config.json') -Raw | ConvertFrom-Json
$config.PubHost = '127.0.0.1'
$config.PullHost = '127.0.0.1'
$config.PubPort = 55665
$config.PullPort = 55666
$config | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $target 'config.json') -Encoding UTF8
$values = @{
    HostPortUnit='StubHostPort0'; DebugPortUnit='StubDebugPort0'; LogPortUnit='StubLogPort0'
    RecordCurrentData=$false; RecordHardwareData=$false
    BaseRecordDirectory=(Join-Path $target 'data'); ChooseRecordDirectory=$false
    HostFrameSourceType=0; HostDataType=4; DebugMcbjSubcommandTime=1000
}
@{Values=$values} | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $target 'settings.json') -Encoding UTF8
$process = Start-Process -FilePath (Join-Path $target 'JinGateway.exe') -WorkingDirectory $target -WindowStyle Hidden -PassThru
$process.Id | Set-Content (Join-Path $target 'check.pid')
Write-Output "Isolated Stub PID: $($process.Id), PUB 55665 / PULL 55666; all COM ports set to Stub."
