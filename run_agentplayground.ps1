# run_agentplayground.ps1
# Run Agent Playground with auto-detected devtunnel endpoint

$EndpointFile = Join-Path $PSScriptRoot ".devtunnel-endpoint"

if (Test-Path $EndpointFile) {
    $BotEndpoint = Get-Content $EndpointFile -Raw
    $BotEndpoint = $BotEndpoint.Trim()
    Write-Host "Using detected endpoint: $BotEndpoint" -ForegroundColor Cyan
} else {
    Write-Warning ".devtunnel-endpoint not found. Make sure run_devtunnel.ps1 is running first."
    Write-Host "Falling back to localhost endpoint..." -ForegroundColor Yellow
    $BotEndpoint = "http://localhost:3978/api/messages"
}

agentsplayground -e $BotEndpoint -c "emulator"
