# Package ingestion Lambda
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# Create packages directory
New-Item -ItemType Directory -Force -Path packages

# --- Ingestion Lambda ---
Write-Host 'Packaging ingestion Lambda...'
$buildDir = 'packages/ingestion_build'
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
New-Item -ItemType Directory -Force -Path $buildDir

Copy-Item -Recurse backend/common $buildDir/common
Copy-Item backend/ingestion/*.py $buildDir/
Copy-Item backend/ingestion/requirements.txt $buildDir/

pip install -r backend/ingestion/requirements.txt -t $buildDir --platform manylinux2014_x86_64 --python-version 3.13 --only-binary=:all: --quiet

# --- Query Lambda ---  
Write-Host 'Packaging query Lambda...'
$buildDir = 'packages/query_build'
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
New-Item -ItemType Directory -Force -Path $buildDir

Copy-Item -Recurse backend/common $buildDir/common
Copy-Item backend/query/*.py $buildDir/
Copy-Item backend/query/requirements.txt $buildDir/

pip install -r backend/query/requirements.txt -t $buildDir --platform manylinux2014_x86_64 --python-version 3.13 --only-binary=:all: --quiet
