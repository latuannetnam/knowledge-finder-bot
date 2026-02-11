# Install Claude Code plugins from project's local marketplace

$MarketplaceName = "knowledge-finder-bot-plugins"
$MarketplacePath = ".\.claude\plugins"
$PluginName = "update-docs"

Write-Host "Installing Claude Code plugins..." -ForegroundColor Cyan

# Check if running from project root
if (-not (Test-Path "$MarketplacePath\.claude-plugin\marketplace.json")) {
    Write-Host "Error: Marketplace not found at $MarketplacePath" -ForegroundColor Red
    Write-Host "Make sure you're running this from the project root directory." -ForegroundColor Yellow
    exit 1
}

# Check if claude CLI is available
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "Error: 'claude' CLI not found." -ForegroundColor Red
    Write-Host "Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code" -ForegroundColor Yellow
    exit 1
}

# Step 1: Register local marketplace (idempotent - skips if already added)
Write-Host "Registering local marketplace..." -ForegroundColor Cyan
$marketplaceList = claude plugin marketplace list 2>&1
if ($marketplaceList -match $MarketplaceName) {
    Write-Host "Marketplace '$MarketplaceName' already registered, updating..." -ForegroundColor Yellow
    claude plugin marketplace update $MarketplaceName
} else {
    claude plugin marketplace add $MarketplacePath
}

# Step 2: Install plugin
Write-Host "Installing $PluginName plugin..." -ForegroundColor Cyan
$pluginList = claude plugin list 2>&1
if ($pluginList -match "$PluginName@$MarketplaceName") {
    Write-Host "Plugin already installed, updating..." -ForegroundColor Yellow
    claude plugin update "$PluginName@$MarketplaceName"
} else {
    claude plugin install "$PluginName@$MarketplaceName" --scope user
}

# Step 3: Enable plugin
Write-Host "Enabling $PluginName plugin..." -ForegroundColor Cyan
claude plugin enable "$PluginName@$MarketplaceName"

Write-Host ""
Write-Host "Plugin installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart Claude Code"
Write-Host "2. Verify: /help | grep update-docs"
Write-Host "3. Use: /update-docs"
