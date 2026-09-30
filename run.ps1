# Night Desk launcher - run from this folder:  .\run.ps1
if (-not $env:DREX_API_KEY) { $env:DREX_API_KEY = Read-Host "Paste your Drex API key (nace_sk_...)" }
python server.py
