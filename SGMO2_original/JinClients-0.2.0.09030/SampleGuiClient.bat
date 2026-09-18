@echo off

set ThisDir=%~dp0.

start pythonw "%ThisDir%\pyclient\SampleGuiClient.py"

exit /b 0
