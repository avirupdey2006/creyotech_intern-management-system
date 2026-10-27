$ErrorActionPreference = "Stop"

$CertDir = "D:\intern-management-system\nginx\certs"
$OpenSSL = "D:\Git\usr\bin\openssl.exe"

if (-not (Test-Path $OpenSSL)) {
    $OpenSSL = (Get-Command openssl -ErrorAction Stop).Source
}

$KeyPath = Join-Path $CertDir "ims.key"
$CrtPath = Join-Path $CertDir "ims.crt"
$ConfPath = Join-Path $CertDir "openssl-san.cnf"

@"
[req]
default_bits       = 2048
distinguished_name = req_distinguished_name
req_extensions     = v3_req
x509_extensions    = v3_req
prompt             = no

[req_distinguished_name]
C  = IN
ST = West Bengal
L  = Kolkata
O  = Intern Management System
OU = Security and DevOps
CN = localhost

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = ims.local
IP.1  = 127.0.0.1
"@ | Set-Content -Path $ConfPath -Encoding ascii

try {
    & $OpenSSL req -x509 -nodes -days 365 -newkey rsa:2048 `
        -keyout $KeyPath `
        -out $CrtPath `
        -config $ConfPath

    if ($LASTEXITCODE -ne 0) {
        throw "OpenSSL failed to generate the certificate."
    }

    Write-Host "[OK] Certificate generated: $CrtPath" -ForegroundColor Green
    Write-Host "[OK] Private key generated: $KeyPath" -ForegroundColor Green
}
finally {
    Remove-Item -Force $ConfPath -ErrorAction SilentlyContinue
}
