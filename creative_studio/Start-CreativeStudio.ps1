$ErrorActionPreference = "Stop"

if (-not $env:OPENAI_API_KEY) {
    $secureKey = Read-Host "Enter your OpenAI API key (input is hidden)" -AsSecureString
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try {
        $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
        Push-Location (Join-Path $PSScriptRoot "..")
        try { python creative_studio\server.py }
        finally { Pop-Location }
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
        Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
    }
}
else {
    Push-Location (Join-Path $PSScriptRoot "..")
    try { python creative_studio\server.py }
    finally { Pop-Location }
}
