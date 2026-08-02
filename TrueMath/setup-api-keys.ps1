# setup-api-keys.ps1
# ------------------------------------------------------------------
# Interactive setup for TrueMath's cloud AI API keys -- no manual .env
# editing needed. Run once:  .\setup-api-keys.ps1
# ------------------------------------------------------------------
$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"
$envExamplePath = Join-Path $repoRoot ".env.example"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TrueMath API Key Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "TrueMath ka Q-and-A/AI feature Groq aur/ya OpenRouter ki FREE API keys use karta hai." -ForegroundColor White
Write-Host "Keys yahan se milti hain (dono free hain):" -ForegroundColor White
Write-Host "  Groq:       https://console.groq.com/keys" -ForegroundColor Yellow
Write-Host "  OpenRouter: https://openrouter.ai/keys" -ForegroundColor Yellow
Write-Host ""
Write-Host "Kam se kam EK key deni zaroori hai. Dono bhi de sakte ho (fallback ke liye)." -ForegroundColor White
Write-Host "Khaali chhodne ke liye bas Enter dabao." -ForegroundColor DarkGray
Write-Host ""

$groqKey = Read-Host "Groq API key paste karo (gsk_... se shuru hoti hai)"
$openrouterKey = Read-Host "OpenRouter API key paste karo (sk-or-... se shuru hoti hai)"

if ([string]::IsNullOrWhiteSpace($groqKey) -and [string]::IsNullOrWhiteSpace($openrouterKey)) {
    Write-Host ""
    Write-Host "WARNING: Koi bhi key nahi di gayi -- Q-and-A AI feature kaam nahi karega jab tak" -ForegroundColor Red
    Write-Host "baad mein .env file mein manually key na daali jaye." -ForegroundColor Red
}

# Start from .env.example if .env doesn't exist yet, else edit existing .env
if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
    } else {
        New-Item -ItemType File -Path $envPath | Out-Null
    }
}

$content = Get-Content $envPath -Raw -ErrorAction SilentlyContinue
if (-not $content) { $content = "" }

function Set-EnvValue {
    param($content, $key, $value)
    if ([string]::IsNullOrWhiteSpace($value)) { return $content }
    $pattern = "(?m)^#?\s*$key=.*$"
    if ($content -match $pattern) {
        return [regex]::Replace($content, $pattern, "$key=$value")
    } else {
        return $content + "`n$key=$value`n"
    }
}

$content = Set-EnvValue $content "TRUEMATH_GROQ_API_KEY" $groqKey
$content = Set-EnvValue $content "TRUEMATH_OPENROUTER_API_KEY" $openrouterKey

Set-Content -Path $envPath -Value $content -NoNewline

Write-Host ""
Write-Host "Done! .env file update ho gayi: $envPath" -ForegroundColor Green
Write-Host "Ab TrueMath start karo (.\start-truemath.ps1 ya Desktop shortcut se)." -ForegroundColor Cyan
Write-Host ""
Write-Host "NOTE: Ye .env file kabhi kisi ke saath share mat karna -- isme tumhari private keys hain." -ForegroundColor Yellow
