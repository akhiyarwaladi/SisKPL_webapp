@ECHO off

set "script_path=%~dp0"
set "script_path=%script_path%server.py"

START runCelery.bat
timeout 8
CALL startTask.bat