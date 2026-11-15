$ErrorActionPreference = "Stop"
$wokwiDir = $PSScriptRoot
$buildStaging = Join-Path $env:TEMP "aqua_wokwi_build"
$pioExe = Join-Path $env:USERPROFILE ".platformio\penv\Scripts\pio.exe"

New-Item -ItemType Directory -Force -Path $buildStaging | Out-Null
Copy-Item -Force (Join-Path $wokwiDir "platformio.ini") (Join-Path $buildStaging "platformio.ini")
Copy-Item -Force (Join-Path $wokwiDir "sketch.ino") (Join-Path $buildStaging "sketch.ino")

$localLibDeps = Join-Path $wokwiDir ".pio\libdeps"
$stagingPio = Join-Path $buildStaging ".pio"
if ((Test-Path $localLibDeps) -and -not (Test-Path (Join-Path $stagingPio "libdeps"))) {
    New-Item -ItemType Directory -Force -Path $stagingPio | Out-Null
    Copy-Item -Recurse -Force $localLibDeps (Join-Path $stagingPio "libdeps")
}

& $pioExe run -d $buildStaging
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$outDir = Join-Path $wokwiDir ".pio\build\esp32dev"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Copy-Item -Force (Join-Path $buildStaging ".pio\build\esp32dev\firmware.bin") (Join-Path $outDir "firmware.bin")
Copy-Item -Force (Join-Path $buildStaging ".pio\build\esp32dev\firmware.elf") (Join-Path $outDir "firmware.elf")
Write-Host "✅ Compiled firmware copied to $outDir" -ForegroundColor Green
