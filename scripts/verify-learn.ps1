param(
    [string]$BaseUrl = "http://127.0.0.1:8080",
    [switch]$SkipApi,
    [switch]$VerifyLatestReport
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http
$Handler = New-Object System.Net.Http.HttpClientHandler
$Handler.AllowAutoRedirect = $false
$Client = New-Object System.Net.Http.HttpClient($Handler)
$Client.Timeout = [TimeSpan]::FromSeconds(15)
$BaseUrl = $BaseUrl.TrimEnd('/')
if ($SkipApi -and $VerifyLatestReport) {
    $Client.Dispose()
    $Handler.Dispose()
    throw "VerifyLatestReport requires a running API; do not combine it with SkipApi."
}

function Get-CheckedResponse([string]$Path, [int]$ExpectedStatus) {
    $Response = $Client.GetAsync("$BaseUrl$Path").GetAwaiter().GetResult()
    if ([int]$Response.StatusCode -ne $ExpectedStatus) {
        $ActualStatus = [int]$Response.StatusCode
        $Response.Dispose()
        throw "$Path returned $ActualStatus; expected $ExpectedStatus"
    }
    Write-Host "PASS $ExpectedStatus $Path"
    return $Response
}

try {
    $Response = Get-CheckedResponse "/learn?verify=1" 308
    try {
        if ([string]$Response.Headers.Location -ne '/learn/?verify=1') {
            throw "The /learn redirect must be relative and preserve query parameters."
        }
    } finally { $Response.Dispose() }

    $Response = Get-CheckedResponse "/learn/" 200
    try {
        if ($Response.Content.Headers.ContentType.MediaType -ne 'text/html') { throw "Expected HTML" }
        if ([string]$Response.Headers.CacheControl -notmatch 'no-cache') { throw "HTML must revalidate" }
        $Html = $Response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if ($Html -notmatch 'Market Intel Lab' -or $Html -notmatch 'id="labs"') { throw "Wrong learning page" }
    } finally { $Response.Dispose() }

    $Assets = @([regex]::Matches($Html, '(?:src|href)="(/[^"#]+)"') | ForEach-Object { $_.Groups[1].Value })
    $Assets += '/learn/market-intel-og.png'
    $Assets = @($Assets | Sort-Object -Unique)
    if (-not ($Assets -match '\.css$') -or -not ($Assets -match '\.js$')) { throw "Missing CSS or JavaScript references" }
    foreach ($Asset in $Assets) {
        if (-not $Asset.StartsWith('/learn/')) { throw "Asset escaped /learn: $Asset" }
        $Response = Get-CheckedResponse $Asset 200
        try {
            $Type = $Response.Content.Headers.ContentType.MediaType
            if ($Type -eq 'text/html') { throw "Asset returned HTML: $Asset" }
            if ($Asset -match '\.css$' -and $Type -ne 'text/css') { throw "Incorrect CSS MIME type" }
            if ($Asset -match '\.js$' -and $Type -notmatch '^(application|text)/javascript$') { throw "Incorrect JS MIME type" }
            if ($Asset.StartsWith('/learn/_next/static/') -and
                [string]$Response.Headers.CacheControl -notmatch 'immutable') { throw "Missing bundle cache policy" }
            if ($Response.Headers.GetValues('X-Content-Type-Options') -notcontains 'nosniff') { throw "Missing nosniff" }
        } finally { $Response.Dispose() }
    }

    foreach ($Path in @('/learn/missing-verification-page/', '/learn/missing-verification-file.svg', '/learn/_next/static/missing-verification-file.js')) {
        $Response = Get-CheckedResponse $Path 404
        try {
            if ([string]$Response.Headers.CacheControl -match 'immutable') { throw "Missing files must not be cached as immutable" }
        } finally { $Response.Dispose() }
    }
    # The help pages are always served by the same Nginx, even without an API.
    foreach ($Path in @('/help.html', '/guide.txt')) {
        $Response = Get-CheckedResponse $Path 200
        $Response.Dispose()
    }
    if (-not $SkipApi) {
        foreach ($Path in @('/', '/health', '/api/docs')) {
            $Response = Get-CheckedResponse $Path 200
            try {
                if ($Path -eq '/health') {
                    $Health = $Response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
                    if ($Health.status -ne 'ok') { throw "API is not healthy" }
                }
            } finally { $Response.Dispose() }
        }
        # A similarly named route must stay with FastAPI, not the static site.
        $Response = Get-CheckedResponse '/learning' 404
        try {
            if ($Response.Content.Headers.ContentType.MediaType -ne 'application/json') {
                throw "The /learning path was incorrectly routed to the learning site."
            }
        } finally { $Response.Dispose() }
    }
    if ($VerifyLatestReport) {
        foreach ($Path in @('/reports/latest', '/reports/latest/download')) {
            $Response = Get-CheckedResponse $Path 200
            try {
                if ($Response.Content.Headers.ContentType.MediaType -ne 'text/html') {
                    throw "Expected an HTML report: $Path"
                }
                if ($Path.EndsWith('/download') -and
                    $Response.Content.Headers.ContentDisposition.DispositionType -ne 'attachment') {
                    throw "The report download must retain its attachment header."
                }
            } finally { $Response.Dispose() }
        }
    }
    Write-Host "PASS: /learn redirect, HTML, assets, MIME, cache, 404 and existing routes." -ForegroundColor Green
} finally {
    $Client.Dispose()
    $Handler.Dispose()
}
