$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendRoot = Join-Path $projectRoot 'frontend'

Start-Process -FilePath 'python' `
  -ArgumentList '-m', 'uvicorn', 'backend.api:app', '--reload', '--port', '8000' `
  -WorkingDirectory $projectRoot `
  -WindowStyle Hidden

Start-Process -FilePath 'npm.cmd' `
  -ArgumentList 'run', 'dev' `
  -WorkingDirectory $frontendRoot `
  -WindowStyle Hidden

Write-Output 'ElaraX is starting:'
Write-Output '  UI:  http://localhost:3000'
Write-Output '  API: http://localhost:8000/docs'
