$ErrorActionPreference = 'Stop'
$checkId = [int](Get-Content (Join-Path $PSScriptRoot '.stub_gateway/check.pid'))
$process = Get-Process -Id $checkId -ErrorAction SilentlyContinue
if (-not $process) { Write-Output 'Isolated Stub already stopped.'; exit }
$expected = Join-Path $PSScriptRoot '.stub_gateway/JinGateway.exe'
if ($process.Path -ne $expected) { throw 'Unexpected process path; not stopping it.' }
$process.CloseMainWindow() | Out-Null
if (-not $process.WaitForExit(5000)) {
    # Only the verified, isolated all-Stub process created by this check.
    Stop-Process -Id $checkId
}
Write-Output 'Isolated Stub Gateway stopped.'
