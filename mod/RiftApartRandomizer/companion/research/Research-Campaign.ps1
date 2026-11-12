<#
.SYNOPSIS
  Randomizer 3.1 campaign research: ONE read-only run that collects what is needed to drive the
  game's mission system (how missions are registered, which actions change mission state, the
  level's checkpoints and story overlays, mission configs, and the code of the mission actions).

.DESCRIPTION
  Start the game with the randomizer (rivet.toml [bridge] on, rando_give.dll loaded), load a
  save, stand anywhere on a planet, then run Research-Campaign.bat. It takes 1-3 minutes.
  Everything goes into campaign_research_<date>.zip next to this script. Send that zip back.

  Read-only: it only uses rivet_hook's query commands (event.classes, event.info,
  level.checkpoints, level.regions, config.list, config.get, script.nodes, script.node,
  mem.read) and the randomizer's own research functions. It changes nothing in the game.
  With -IncludeSaves (default) it also copies your save folder, and with -IncludeDag the
  game's dag (asset names), into the zip, so mission states and names can be decoded offline.
#>
param(
    [string]$PipeName = "rivet_hook",
    [string]$GameDir = "",
    [switch]$NoSaves,
    [switch]$NoDag,
    [string]$OutDir = ""
)
$ErrorActionPreference = "Stop"
if ($OutDir -eq "") { $OutDir = $PSScriptRoot }
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("rando_research_" + $stamp)
New-Item -ItemType Directory -Path $work | Out-Null

function Read-Exactly([System.IO.Stream]$stream, [int]$count) {
    $buffer = New-Object byte[] $count
    $read = 0
    while ($read -lt $count) {
        $n = $stream.Read($buffer, $read, $count - $read)
        if ($n -le 0) { throw "pipe closed mid-message" }
        $read += $n
    }
    return ,$buffer
}
function Invoke-Bridge([string]$request) {
    for ($try = 0; $try -lt 5; $try++) {
        $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $PipeName, [System.IO.Pipes.PipeDirection]::InOut)
        try {
            $pipe.Connect(4000)
            $payload = [System.Text.Encoding]::UTF8.GetBytes($request)
            $pipe.Write([BitConverter]::GetBytes([uint32]$payload.Length), 0, 4)
            $pipe.Write($payload, 0, $payload.Length)
            $pipe.Flush()
            $length = [BitConverter]::ToUInt32((Read-Exactly $pipe 4), 0)
            return ([System.Text.Encoding]::UTF8.GetString((Read-Exactly $pipe ([int]$length))) | ConvertFrom-Json)
        } catch {
            if ($try -eq 4) { throw }
            Start-Sleep -Milliseconds 300
        } finally { $pipe.Dispose() }
    }
}
function Get-Result([string]$request) {
    $r = Invoke-Bridge $request
    if ($r.ok) { return $r.result }
    return [ordered]@{ error = $r.error; request = $request }
}
function Invoke-Lua([string]$chunk) {
    $r = Invoke-Bridge ("script.exec " + $chunk)
    if (-not $r.ok) { throw "script.exec failed: $($r.error)" }
    return [string]$r.result.value
}
function Save-Json($name, $value) {
    ConvertTo-Json -InputObject $value -Depth 12 -Compress | Set-Content -LiteralPath (Join-Path $work $name) -Encoding UTF8
}

$Keywords = 'Mission|Objective|Story|Campaign|Checkpoint|Planet|Level|Travel|Warp|Collect|Spybot|Ryno|Lorb|Craig|Vanity|Armor|GoldBolt|Gold|Save|Quest|Arena|Boss|Overlay|Region|Unlock|Progress|NewGame|Replay|Galactic|Dimension|Rift|Vendor|Currency|Raritanium|Health|Upgrade'
$summary = [ordered]@{ tool = "Research-Campaign 3.1"; started = (Get-Date).ToString("s"); steps = [ordered]@{} }

# rivet_hook's bridge splits a request at spaces and knows no quotes, and its filters are
# case-sensitive substrings: lists are asked for once per keyword and merged (3.0 sent "" as the
# filter, which matched nothing - round 14)
function Get-Merged([string]$command, [string[]]$filters, [string]$field, [int]$limit) {
    $seen = [ordered]@{}
    foreach ($f in $filters) {
        $r = Get-Result ("$command $f $limit")
        $list = @()
        if ($r -is [System.Array]) { $list = $r } elseif ($r.$field) { $list = $r.$field }
        foreach ($x in $list) {
            $key = if ($x -is [string]) { $x } elseif ($x.name) { "$($x.name)" } elseif ($x.id) { "$($x.id)" } else { ($x | ConvertTo-Json -Compress -Depth 3) }
            if (-not $seen.Contains($key)) { $seen[$key] = $x }
        }
    }
    return ,@($seen.Values)                    # the comma keeps a one-item list a list
}
$EventWords = @("Mission", "Objective", "Story", "Planet", "Level", "Checkpoint", "Travel", "Warp", "Save", "Collect",
                "Spybot", "Ryno", "Lorb", "Craig", "Vanity", "Armor", "Gold", "Arena", "Boss", "Region", "Unlock",
                "Progress", "Replay", "Rift", "Vendor", "Currency", "Upgrade", "Health", "Quest", "Overlay")

Write-Host "1/7 event classes"
$classes = Get-Merged "event.classes" $EventWords "classes" 2000
Save-Json "event_classes.json" $classes
$info = [ordered]@{}
$names = $classes | ForEach-Object { if ($_ -is [string]) { $_ } else { $_.name } }
foreach ($n in $names) { if ($n -and $n -match $Keywords) { $info[$n] = Get-Result ("event.info " + $n) } }
Save-Json "event_info.json" $info
$summary.steps.events = "$($names.Count) classes, $($info.Count) described"

Write-Host "2/7 checkpoints and regions"
$cps = Get-Merged "level.checkpoints" @("CHK", "_") "checkpoints" 5000
Save-Json "checkpoints.json" $cps
$regs = Get-Merged "level.regions" @("_", "MIS", "mis", "Story", "story", "/") "regions" 5000
Save-Json "regions.json" $regs
$summary.steps.level = "$(@($cps).Count) checkpoints, $(@($regs).Count) regions"

Write-Host "3/7 configs"
$items = Get-Merged "config.list" @("Mission", "mission", "Objective", "Planet", "Level", "Story", "Vanity", "Reward", "Currency") "configs" 5000
Save-Json "config_list.json" $items
$cfgs = [ordered]@{}
$count = 0
foreach ($c in $items) {
    $t = "$($c.type)"
    if ($t -match $Keywords -and $count -lt 800) { $cfgs["$($c.id)"] = Get-Result ("config.get " + $c.id); $count++ }
}
Save-Json "configs.json" $cfgs
$summary.steps.configs = "$($items.Count) loaded, $count dumped"

Write-Host "4/7 level-script nodes of the mission system"
$Actions = @("StartMissionAction","MakeMissionAvailableAction","CompleteMissionAction","SetMissionActiveAction",
             "DeactivateMissionAction","SaveMissionStateAction","ReplayMissionAction","AbandonMissionAction","FailMissionAction",
             "CheckMissionStateAction","CheckMissionAction","AnyMissionActiveAction","AdvanceMissionObjectiveAction",
             "CompleteMissionObjectiveAction","StartMissionObjectiveAction","SkipObjectiveAction","ReloadToObjectiveAction",
             "UnlockLevelAction","IsLevelUnlockedAction","SetPlanetaryTravelAction","CheckPlanetaryTravelAction",
             "OverridePlanetLandingCheckpointAction","PlanetMenuCheckpointWarpAction","CheckpointWarpAction","LoadLevelAction",
             "GlobalSaveTableSetKeyAction","GlobalSaveTableQueryAction","GlobalSaveTableCheckKeyAction","HasVisitedLevelAction",
             "OnMissionStateChangeEventAction","IsMissionReplayAction","VanityGiveBundleAction","VanityGiveSetAction",
             "AddCurrencyAction","SetWeaponLevelAction","CollectibleCollectAction","AddToInventoryAction")
$nodes = [ordered]@{}
$detail = 0
foreach ($a in $Actions) {
    $list = Get-Result ("script.nodes " + $a + " 200")
    $nodes[$a] = [ordered]@{ list = $list; detail = @() }
    $arr = @()
    if ($list -is [System.Array]) { $arr = $list } elseif ($list.nodes) { $arr = $list.nodes }
    foreach ($n in ($arr | Select-Object -First 12)) {
        if ($n.class -eq $a -and $detail -lt 300) {
            $nodes[$a].detail += ,(Get-Result ("script.node " + $n.component))
            $detail++
        }
    }
}
Save-Json "script_nodes.json" $nodes
$summary.steps.nodes = "$detail nodes described"

Write-Host "5/7 the randomizer's own research (missions seen, node scan)"
try {
    $st = (Invoke-Lua "return rando_research_status()").Split("|")
    $parts = New-Object System.Collections.Generic.List[string]
    for ($i = 1; $i -le [int]$st[1]; $i++) { $parts.Add((Invoke-Lua "return rando_research_chunk($i)")) }
    [System.IO.File]::WriteAllText((Join-Path $work "randomizer_research.lua"), [string]::Join("", $parts))
    $summary.steps.randomizer = "ok"
} catch { $summary.steps.randomizer = "failed: $_" }

Write-Host "6/7 game code of the mission actions (read-only)"
try {
    & (Join-Path $PSScriptRoot "Dump-GameCode.ps1") -PipeName $PipeName -Out (Join-Path $work "game_code_dump.json") -Extended
    $summary.steps.code = "ok"
} catch { $summary.steps.code = "failed: $_" }

Write-Host "7/7 files"
if ($GameDir -eq "") {
    $p = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    foreach ($cand in @($p, (Split-Path -Parent $p))) { if (Test-Path -LiteralPath (Join-Path $cand "RiftApart.exe")) { $GameDir = $cand } }
}
if ($GameDir -ne "") {
    foreach ($f in @("rivet.log", "rivet.toml")) {
        $src = Join-Path $GameDir $f
        if (Test-Path -LiteralPath $src) { Copy-Item -LiteralPath $src -Destination $work }
    }
    if (-not $NoDag -and (Test-Path -LiteralPath (Join-Path $GameDir "dag"))) { Copy-Item -LiteralPath (Join-Path $GameDir "dag") -Destination $work; $summary.steps.dag = "copied" }
} else { $summary.steps.files = "game folder not found (use -GameDir)" }
if (-not $NoSaves) {
    $cands = @((Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Ratchet & Clank Rift Apart"),
               (Join-Path $env:USERPROFILE "Saved Games\Ratchet & Clank Rift Apart"),
               (Join-Path $env:LOCALAPPDATA "Ratchet & Clank Rift Apart"))
    $found = $null
    foreach ($c in $cands) { if ($c -and (Test-Path -LiteralPath $c)) { $found = $c; break } }
    if ($found) {
        Copy-Item -LiteralPath $found -Destination (Join-Path $work "saves") -Recurse
        $summary.steps.saves = "copied from $found"
    } else { $summary.steps.saves = "not found (optional; tried: $($cands -join '; '))" }
}
$summary.finished = (Get-Date).ToString("s")
Save-Json "summary.json" $summary

$zip = Join-Path $OutDir ("campaign_research_" + $stamp + ".zip")
Compress-Archive -Path (Join-Path $work "*") -DestinationPath $zip
Remove-Item -LiteralPath $work -Recurse -Force
Write-Host "written $zip - send this file back."
