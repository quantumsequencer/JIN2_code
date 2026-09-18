@echo off

set ThisDir=%~dp0.

start pythonw "%ThisDir%\pyclient\MeasurementWizard.py"

exit /b 0
