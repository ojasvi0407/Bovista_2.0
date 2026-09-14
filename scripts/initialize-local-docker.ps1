[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$targetPath = Join-Path $repositoryRoot ".env.local-docker"

if ((Test-Path -LiteralPath $targetPath) -and -not $Force) {
    throw ".env.local-docker already exists. Re-run with -Force to replace it."
}

function New-SecureBase64Value {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ByteCount,
        [switch]$PreservePadding
    )

    $bytes = New-Object byte[] $ByteCount
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }

    $value = [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_")
    if (-not $PreservePadding) {
        $value = $value.TrimEnd("=")
    }
    return $value
}

$lines = @(
    "# Generated for PashuMitra local Docker deployment. Do not commit this file."
    "POSTGRES_PASSWORD=$(New-SecureBase64Value -ByteCount 48)"
    "DATABASE_PASSWORD=$(New-SecureBase64Value -ByteCount 48)"
    "WORKER_DATABASE_PASSWORD=$(New-SecureBase64Value -ByteCount 48)"
    "AUDIT_HMAC_KEY=$(New-SecureBase64Value -ByteCount 48)"
    "JWT_SIGNING_KEY=$(New-SecureBase64Value -ByteCount 48)"
    "REFRESH_TOKEN_PEPPER=$(New-SecureBase64Value -ByteCount 48)"
    "OTP_HMAC_KEY=$(New-SecureBase64Value -ByteCount 48)"
    "MFA_ENCRYPTION_KEY=$(New-SecureBase64Value -ByteCount 32 -PreservePadding)"
    "WORKER_USER_ID=00000000-0000-0000-0000-000000000001"
    "EVENT_DELIVERY_URL=https://127.0.0.1:9443/events"
    "EVENT_DELIVERY_TOKEN=$(New-SecureBase64Value -ByteCount 48)"
)

$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($targetPath, $lines, $utf8WithoutBom)
Write-Output "Created $targetPath"
