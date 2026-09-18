$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$checkId = [int](Get-Content (Join-Path $PSScriptRoot '.stub_gateway/check.pid'))
$expected = Join-Path $PSScriptRoot '.stub_gateway/JinGateway.exe'
if ((Get-Process -Id $checkId).Path -ne $expected) { throw 'Unexpected process path' }
$condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, $checkId)
$scope = [System.Windows.Automation.TreeScope]::Descendants
$all = [System.Windows.Automation.Condition]::TrueCondition
$windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
$main = $windows | Where-Object {$_.Current.Name -eq 'Host Application'}
$menu = $main.FindAll($scope, $all) | Where-Object {$_.Current.Name -eq 'Tools(T)' -and $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::MenuItem}
$expand = $menu.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
$expand.Expand()
Start-Sleep -Milliseconds 200
$stub = $menu.FindAll($scope, $all) | Where-Object {$_.Current.Name -like '*Stub*' -and $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::MenuItem} | Select-Object -First 1
if (-not $stub) { throw 'Stub menu not found' }
$stub.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
Start-Sleep -Milliseconds 300
$windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
$window = $windows | Where-Object {$_.Current.Name -like '*Stub*'} | Select-Object -First 1
$start = $window.FindAll($scope, $all) | Where-Object {$_.Current.Name -eq 'Start' -and $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button} | Select-Object -First 1
if (-not $start) { throw 'Stub Start button not found' }
$start.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
Write-Output 'Started Host data generation on isolated Gateway Stub.'
