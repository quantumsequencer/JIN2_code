$ErrorActionPreference = 'Stop'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$installation = & $vswhere -latest -products '*' -requires Microsoft.Component.MSBuild -property installationPath
if (-not $installation) { throw 'Visual Studio with MSBuild was not found.' }
$sdkRoot = Join-Path $env:ProgramFiles 'dotnet'
$env:DOTNET_ROOT = $sdkRoot
$env:DOTNET_MSBUILD_SDK_RESOLVER_CLI_DIR = $sdkRoot
$env:PATH = "$sdkRoot;$env:PATH"
$builder = Join-Path $installation 'MSBuild/Current/Bin/amd64/MSBuild.exe'
& $builder (Join-Path $PSScriptRoot 'gateway_source/Gateway.slnx') /restore /p:Configuration=Release /nologo /verbosity:minimal
exit $LASTEXITCODE
