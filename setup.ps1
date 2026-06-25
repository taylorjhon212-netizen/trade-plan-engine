# Run this once to set environment variables for local use
# (GitHub Actions uses repo secrets instead)

$token = Read-Host "Enter TELEGRAM_TOKEN (or press Enter to skip)"
$chatId = Read-Host "Enter TELEGRAM_CHAT_ID (or press Enter to skip)"

if ($token) { [Environment]::SetEnvironmentVariable("TELEGRAM_TOKEN", $token, "User") }
if ($chatId) { [Environment]::SetEnvironmentVariable("TELEGRAM_CHAT_ID", $chatId, "User") }

Write-Host "Done. Restart your terminal for changes to take effect."
