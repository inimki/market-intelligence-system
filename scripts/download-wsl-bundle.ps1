$ErrorActionPreference = "Stop"

$Url = "https://github.com/microsoft/WSL/releases/download/2.7.12/Microsoft.WSL_2.7.12.0_x64_ARM64.msixbundle"
$DownloadRoot = Join-Path (Split-Path -Parent $PSScriptRoot) ".downloads\wsl"
$PartsDir = [System.IO.Path]::GetFullPath((Join-Path $DownloadRoot "parts"))
$OutputPath = [System.IO.Path]::GetFullPath((Join-Path $DownloadRoot "Microsoft.WSL_2.7.12.0_x64_ARM64.msixbundle"))
$ExpectedTotal = [int64]518988532
$ExpectedHash = "deb1499e0fa081f7e7933e034195eb65b0302d84d8f2e9d5b3c5466bf6d952cc"
$PartCount = 16
$PartSize = [math]::Ceiling($ExpectedTotal / $PartCount)

New-Item -ItemType Directory -Path $PartsDir -Force | Out-Null
$Jobs = @()

for ($Index = 0; $Index -lt $PartCount; $Index++) {
    $Start = [int64]($Index * $PartSize)
    $End = [math]::Min([int64](($Index + 1) * $PartSize - 1), [int64]($ExpectedTotal - 1))
    $PartPath = [System.IO.Path]::GetFullPath((Join-Path $PartsDir ("part-{0:D2}.bin" -f $Index)))
    if (-not $PartPath.StartsWith($PartsDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Part path escaped the verified download directory."
    }
    $ExpectedPartLength = $End - $Start + 1
    $CurrentLength = if (Test-Path -LiteralPath $PartPath) {
        (Get-Item -LiteralPath $PartPath).Length
    }
    else {
        0
    }
    if ($CurrentLength -eq $ExpectedPartLength) {
        continue
    }
    if ($CurrentLength -gt $ExpectedPartLength) {
        throw "Part $Index is larger than expected."
    }

    $ResumeStart = $Start + $CurrentLength
    $Jobs += Start-Job -ScriptBlock {
        param($DownloadUrl, $RangeStart, $RangeEnd, $Part, $ExpectedLength)
        $RemainingPath = "$Part.remaining"
        & curl.exe `
            --fail `
            --location `
            --proxy http://127.0.0.1:10808 `
            --connect-timeout 20 `
            --speed-time 20 `
            --speed-limit 1024 `
            --retry 50 `
            --retry-all-errors `
            --retry-delay 2 `
            --range "$RangeStart-$RangeEnd" `
            --output $RemainingPath `
            $DownloadUrl 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "curl failed with exit code $LASTEXITCODE."
        }
        $Target = [System.IO.File]::Open(
            $Part,
            [System.IO.FileMode]::Append,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        try {
            $Source = [System.IO.File]::OpenRead($RemainingPath)
            try {
                $Source.CopyTo($Target)
            }
            finally {
                $Source.Dispose()
            }
        }
        finally {
            $Target.Dispose()
        }
        if ((Get-Item -LiteralPath $Part).Length -ne $ExpectedLength) {
            throw "Resumed range size mismatch."
        }
    } -ArgumentList $Url, $ResumeStart, $End, $PartPath, $ExpectedPartLength
}

while ($Jobs | Where-Object State -eq "Running") {
    Start-Sleep -Seconds 30
    $StoredBytes = (
        Get-ChildItem -LiteralPath $PartsDir -File |
            Where-Object Name -Like "part-*.bin" |
            Measure-Object Length -Sum
    ).Sum
    $InFlightBytes = (
        Get-ChildItem -LiteralPath $PartsDir -File |
            Where-Object Name -Like "*.remaining" |
            Measure-Object Length -Sum
    ).Sum
    if (-not $InFlightBytes) {
        $InFlightBytes = 0
    }
    $CompletedJobs = ($Jobs | Where-Object State -eq "Completed").Count
    $FailedJobs = ($Jobs | Where-Object State -eq "Failed").Count
    Write-Host (
        "WSL progress: stored {0:N1} MiB + downloading {1:N1} MiB / {2:N1} MiB; jobs {3}/{4}, failed {5}" -f `
            ($StoredBytes / 1MB),
            ($InFlightBytes / 1MB),
            ($ExpectedTotal / 1MB),
            $CompletedJobs,
            $Jobs.Count,
            $FailedJobs
    )
}

$Jobs | Wait-Job | Out-Null
$Failed = $Jobs | Where-Object State -ne "Completed"
if ($Failed) {
    $Failed | Receive-Job
    throw "One or more WSL downloads failed."
}

$OrderedParts = Get-ChildItem -LiteralPath $PartsDir -Filter "part-*.bin" | Sort-Object Name
if ($OrderedParts.Count -ne $PartCount) {
    throw "Expected $PartCount parts, found $($OrderedParts.Count)."
}
$PartsTotal = ($OrderedParts | Measure-Object Length -Sum).Sum
if ($PartsTotal -ne $ExpectedTotal) {
    throw "Part total is $PartsTotal, expected $ExpectedTotal."
}

$TargetStream = [System.IO.File]::Open(
    $OutputPath,
    [System.IO.FileMode]::Create,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::None
)
try {
    foreach ($Part in $OrderedParts) {
        $SourceStream = [System.IO.File]::OpenRead($Part.FullName)
        try {
            $SourceStream.CopyTo($TargetStream)
        }
        finally {
            $SourceStream.Dispose()
        }
    }
}
finally {
    $TargetStream.Dispose()
}

$ActualHash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualHash -ne $ExpectedHash) {
    throw "WSL bundle SHA256 mismatch."
}
Write-Host "WSL bundle download and SHA256 verification succeeded: $OutputPath"
