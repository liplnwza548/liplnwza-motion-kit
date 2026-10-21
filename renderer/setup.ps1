$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python venv failed" }
& .\.venv\Scripts\python.exe -m pip install -r renderer\requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
& .\.venv\Scripts\python.exe renderer\kit.py doctor
if ($LASTEXITCODE -ne 0) { throw "Resolve doctor failures, including FFmpeg/FFprobe, before rendering" }
