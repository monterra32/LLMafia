# open-mafia.ps1
<#
  Launch a full Mafia run in Windows Terminal:
    • 1 tab for setup (prepare_game → mafia_main)
    • m tabs for LLM players
    • n–m tabs for human players

  ─────────── EDIT THESE ───────────
#>
$AnacondaRoot   = 'C:\Users\cococ\anaconda3'                              # ← your conda root
$EnvName        = 'LLMafia-env'                                          # ← your env name
$TargetDir      = 'C:\Users\cococ\Documents\GitHub\LLMafia'              # ← your project folder
$ConfigFileName = 'openai_3_3.json'                                      # ← your JSON config (word_n_m.json)
#───────────────────────────────────────────────────

# Build paths
$hookScript     = Join-Path $AnacondaRoot 'shell\condabin\conda-hook.ps1'
$ConfigFilePath = Join-Path $TargetDir $ConfigFileName
$baseName       = [IO.Path]::GetFileNameWithoutExtension($ConfigFileName)

# Extract n (total players) and m (LLMs):
if ($baseName -match '^[^_]+_(\d+)_(\d+)$') {
    $n = [int]$matches[1]
    $m = [int]$matches[2]
} else {
    Write-Error "ConfigFileName must be in the form word_n_m.json (e.g. openai_3_3.json)"
    exit 1
}

# Helper: wrap hook+activate+cd + your body in ONE quoted string
function Get-TabCommand {
    param($body)
    $full = "& '$hookScript';conda activate '$EnvName';Set-Location -Path '$TargetDir';$body"
    # Surround with double‐quotes so -Command sees it as one string
    return "`"$full`""
}

# Build Windows-Terminal arguments
$wtArgs = @()

# ── Tab 1: Setup (prepare_game → mafia_main) ───────────────────
$wtArgs += 'new-tab'
$wtArgs += 'powershell.exe'
$wtArgs += '-NoExit'
$wtArgs += '-ExecutionPolicy'; $wtArgs += 'Bypass'
$wtArgs += '-Command'
$wtArgs += Get-TabCommand("python prepare_game.py -c '$ConfigFilePath'; python .\mafia_main.py")

# ── Next m tabs: LLM interfaces ────────────────────────────────
for ($i = 1; $i -le $m; $i++) {
    $wtArgs += 'new-tab'
    $wtArgs += 'powershell.exe'
    $wtArgs += '-NoExit'
    $wtArgs += '-ExecutionPolicy'; $wtArgs += 'Bypass'
    $wtArgs += '-Command'
    $wtArgs += Get-TabCommand("echo $i | python .\llm_interface.py")
}

# ── Next (n-m) tabs: human players ─────────────────────────────
$humanCount = $n - $m
for ($j = 1; $j -le $humanCount; $j++) {
    $wtArgs += 'new-tab'
    $wtArgs += 'powershell.exe'
    $wtArgs += '-NoExit'
    $wtArgs += '-ExecutionPolicy'; $wtArgs += 'Bypass'
    $wtArgs += '-Command'
    $wtArgs += Get-TabCommand("echo $j | python .\player_merged_chat_and_input.py")
}

# Finally: launch Windows Terminal with all tabs
Start-Process 'wt.exe' -ArgumentList $wtArgs
