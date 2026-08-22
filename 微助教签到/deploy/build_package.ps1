$ErrorActionPreference = "Stop"

$builder = Join-Path $PSScriptRoot "build_package.py"
python $builder
if ($LASTEXITCODE -ne 0) {
    throw "deploy.zip build failed with exit code $LASTEXITCODE"
}
