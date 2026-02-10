# run_devtunnel.ps1
# Script to manage persistent devtunnel for the bot

$ErrorActionPreference = "Stop"

# --- 1. Load Config ---
$EnvFilePath = Join-Path $PSScriptRoot ".env"
$Port = 3978 # Default

if (Test-Path $EnvFilePath) {
    Get-Content $EnvFilePath | ForEach-Object {
        if ($_ -match "^\s*PORT\s*=\s*(\d+)") {
            $Port = $matches[1]
        }
    }
    Write-Host "Loaded configuration from .env. Port: $Port" -ForegroundColor Cyan
} else {
    Write-Host ".env file not found. Using default port: $Port" -ForegroundColor Yellow
}

# Tunnel Configuration
$TunnelId = "knowledge-finder-bot"

# --- 2. Check Prereqs ---
if (-not (Get-Command devtunnel -ErrorAction SilentlyContinue)) {
    Write-Error "devtunnel CLI not found. Please install it: winget install Microsoft.Devtunnels"
    exit 1
}

# --- 3. Login Check ---
Write-Host "Checking login status..." -ForegroundColor Gray
try {
    $null = devtunnel user show 2>&1
    Write-Host "Authenticated." -ForegroundColor Green
} catch {
    Write-Host "Not authenticated. Launching login..." -ForegroundColor Yellow
    devtunnel user login
}

# --- 4. Create/Configure Tunnel ---
Write-Host "Checking tunnel '$TunnelId'..." -ForegroundColor Gray
$TunnelListJson = devtunnel list --json | ConvertFrom-Json
$ExistingTunnel = $TunnelListJson.tunnels | Where-Object { $_.tunnelId -like "$TunnelId*" }

if (-not $ExistingTunnel) {
    Write-Host "Creating persistent tunnel '$TunnelId'..." -ForegroundColor Yellow
    devtunnel create $TunnelId --allow-anonymous --expiration 30d
} else {
    Write-Host "Tunnel '$($ExistingTunnel.tunnelId)' exists." -ForegroundColor Green
}

# --- 5. Ensure Port is Mapped ---
Write-Host "Checking port $Port..." -ForegroundColor Gray
try {
    $PortInfo = devtunnel port show $TunnelId -p $Port --json 2>&1 | ConvertFrom-Json
    Write-Host "Port $Port already configured." -ForegroundColor Green
} catch {
    Write-Host "Creating port $Port..." -ForegroundColor Yellow
    devtunnel port create $TunnelId -p $Port --protocol http
}

# --- 6. Check if Tunnel is Already Hosted ---
Write-Host "Checking if tunnel is already hosted..." -ForegroundColor Gray
$TunnelStatus = devtunnel show $TunnelId --json | ConvertFrom-Json
if ($TunnelStatus.tunnel.hostConnections -gt 0) {
    Write-Host "Tunnel is already being hosted (Host connections: $($TunnelStatus.tunnel.hostConnections))." -ForegroundColor Yellow
    Write-Host "If you need the endpoint URL, check the .devtunnel-endpoint file or the existing host process." -ForegroundColor Cyan

    # Try to read saved endpoint if available
    $EndpointFile = Join-Path $PSScriptRoot ".devtunnel-endpoint"
    if (Test-Path $EndpointFile) {
        $SavedEndpoint = Get-Content $EndpointFile -Raw
        Write-Host "Saved endpoint: $SavedEndpoint" -ForegroundColor Magenta
    }

    Write-Host "Exiting. Stop the existing host process first if you need to restart." -ForegroundColor Yellow
    exit 0
}

# --- 7. Start Tunnel and Capture URL ---
Write-Host "Starting tunnel host..." -ForegroundColor Cyan

# Start the host process in background to capture output while it runs
$Job = Start-Job -ScriptBlock {
    param($TunnelId)
    devtunnel host $TunnelId --allow-anonymous
} -ArgumentList $TunnelId

# Wait for output and capture the URL
$EndpointCaptured = $false
$Timeout = 30 # seconds
$Elapsed = 0

while (-not $EndpointCaptured -and $Elapsed -lt $Timeout) {
    Start-Sleep -Milliseconds 500
    $Elapsed += 0.5

    # Get job output stream
    $Output = Receive-Job -Job $Job 2>&1

    foreach ($Line in $Output) {
        Write-Host $Line

        if ($Line -match "Connect via browser: (https://[^\s]+)") {
            $TunnelUrl = $matches[1]
            $BotEndpoint = "$TunnelUrl/api/messages"

            # Save to file for other scripts to use
            $BotEndpoint | Set-Content (Join-Path $PSScriptRoot ".devtunnel-endpoint")
            Write-Host "`nBot Endpoint: $BotEndpoint" -ForegroundColor Magenta
            $EndpointCaptured = $true
            break
        }
    }
}

if (-not $EndpointCaptured) {
    Write-Warning "Failed to capture tunnel endpoint URL within $Timeout seconds."
} else {
    Write-Host "`nTunnel is now running. Press Ctrl+C to stop." -ForegroundColor Cyan
}

# Wait for the job (keeps script running and forwards output)
try {
    while ($Job.State -eq 'Running') {
        $Output = Receive-Job -Job $Job 2>&1
        foreach ($Line in $Output) {
            Write-Host $Line
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    # Cleanup on exit
    Stop-Job -Job $Job -ErrorAction SilentlyContinue
    Remove-Job -Job $Job -ErrorAction SilentlyContinue
    Write-Host "`nTunnel stopped." -ForegroundColor Yellow
}
