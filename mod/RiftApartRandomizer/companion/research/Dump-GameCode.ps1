<#
.SYNOPSIS
  READ-ONLY research tool for Randomizer 2.x: copies the game code of a few level-script
  actions out of the running game, so armor, currency and upgrade rewards can be added to
  rando_give.dll the same verified way weapons and gadgets were.

.DESCRIPTION
  Start the game with the randomizer installed (rivet.toml [bridge] enabled, rando_give.dll
  loaded), load into a planet, then run Dump-GameCode.bat. It only READS memory through
  rivet_hook's bridge command "mem.read" and writes game_code_dump.json next to this script.
  Nothing in the game is changed. Send game_code_dump.json back (it is a few hundred KB).

  What it reads, for each action below: the action's vtable (from the address the exe's RTTI
  gives, see extras\dev_tools\06_rando_vtables.lua), its first 24 entries, 0x600 bytes of each
  of slots 8-12 (the handlers), and 0x200 bytes at every call target inside them (one level).
#>
param(
    [string]$PipeName = "rivet_hook",
    [string]$Out = "",
    [switch]$Extended          # also the mission-system actions (Research-Campaign uses this)
)
$ErrorActionPreference = "Stop"
if ($Out -eq "") { $Out = Join-Path $PSScriptRoot "game_code_dump.json" }

# script action -> vtable RVA in RiftApart.exe 3.0630.1.0 (from 06_rando_vtables.lua)
$Actions = [ordered]@{
    "AddToInventoryAction"     = 0x2FA4DE0   # reference: already understood (rando_give.dll)
    "VanityGiveBundleAction"   = 0x2FA9218   # armor piece
    "VanityGiveSetAction"      = 0x2FA9290   # armor set
    "AddCurrencyAction"        = 0x2FCEAE8   # bolts / raritanium
    "SetWeaponLevelAction"     = 0x2FFD888   # weapon upgrades
    "UnlockLevelAction"        = 0x2FAEC20   # planet unlock
    "SetPlanetaryTravelAction" = 0x2F2BAA0   # planet menu travel
    "CollectibleCollectAction" = 0x45B4C08   # collectibles
    "SpawnRewardAction"        = 0x2FCEF20
}
if ($Extended) {
    # the mission system (vtable RVAs from the exe's RTTI, 06_rando_vtables.lua)
    $Actions["StartMissionAction"]               = 0x45EDEA0
    $Actions["MakeMissionAvailableAction"]       = 0x45EDDF8
    $Actions["CompleteMissionAction"]            = 0x45EDF40
    $Actions["SetMissionActiveAction"]           = 0x45F99C8
    $Actions["DeactivateMissionAction"]          = 0x45ED240
    $Actions["SaveMissionStateAction"]           = 0x45EDFE0
    $Actions["ReplayMissionAction"]              = 0x45F9DB8
    $Actions["CheckMissionStateAction"]          = 0x45F9950
    $Actions["AdvanceMissionObjectiveAction"]    = 0x45ED600
    $Actions["SkipObjectiveAction"]              = 0x2FBD270
    $Actions["ReloadToObjectiveAction"]          = 0x2FAAF38
    $Actions["OverridePlanetLandingCheckpointAction"] = 0x2FC6920
    $Actions["PlanetMenuCheckpointWarpAction"]   = 0x2FC69A8
    $Actions["CheckpointWarpAction"]             = 0x2F5D1A8
    $Actions["LoadLevelAction"]                  = 0x45D56A0
    $Actions["GlobalSaveTableSetKeyAction"]      = 0x46082A0
    $Actions["IsLevelUnlockedAction"]            = 0x2FAEC98
}
$Mailbox = 0x7FEF00000000
$Candidates = @(0x7FEF00000000, 0x7FEE00000000, 0x7FED00000000, 0x0000000B00000000)

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
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $PipeName, [System.IO.Pipes.PipeDirection]::InOut)
    try {
        $pipe.Connect(3000)
        $payload = [System.Text.Encoding]::UTF8.GetBytes($request)
        $pipe.Write([BitConverter]::GetBytes([uint32]$payload.Length), 0, 4)
        $pipe.Write($payload, 0, $payload.Length)
        $pipe.Flush()
        $length = [BitConverter]::ToUInt32((Read-Exactly $pipe 4), 0)
        return ([System.Text.Encoding]::UTF8.GetString((Read-Exactly $pipe ([int]$length))) | ConvertFrom-Json)
    } finally { $pipe.Dispose() }
}
function Read-Bytes([UInt64]$address, [int]$length) {
    $r = Invoke-Bridge ("mem.read 0x{0:X} {1}" -f $address, $length)
    if (-not $r.ok) { return $null }
    $hex = ($r.result.bytes -replace '[^0-9A-Fa-f]', '')
    $bytes = New-Object byte[] ($hex.Length / 2)
    for ($i = 0; $i -lt $bytes.Length; $i++) { $bytes[$i] = [Convert]::ToByte($hex.Substring($i * 2, 2), 16) }
    return ,$bytes
}
function Hex([byte[]]$b) { if ($null -eq $b) { return $null }; return ([BitConverter]::ToString($b) -replace '-', '') }

# the exe's load address, from rando_give.dll's mailbox (MB_BASE at +0x30)
$base = $null
foreach ($c in $Candidates) {
    $m = Read-Bytes $c 0x38
    if ($null -ne $m -and [System.Text.Encoding]::ASCII.GetString($m, 0, 8) -eq "RANDGIV1") {
        $base = [BitConverter]::ToUInt64($m, 0x30); $Mailbox = $c; break
    }
}
if ($null -eq $base) { throw "rando_give.dll's mailbox was not found - is the game running with the randomizer and rando_give.dll?" }
Write-Host ("exe base 0x{0:X}" -f $base)

$dump = [ordered]@{ tool = "Dump-GameCode 3.1"; exe_base = ("0x{0:X}" -f $base); actions = [ordered]@{}; targets = [ordered]@{} }
$targets = @{}
foreach ($name in $Actions.Keys) {
    $vt = $base + [UInt64]$Actions[$name]
    $vbytes = Read-Bytes $vt (24 * 8)
    if ($null -eq $vbytes) { Write-Host "  $name : vtable not readable"; continue }
    $slots = @()
    for ($i = 0; $i -lt 24; $i++) { $slots += ("0x{0:X}" -f [BitConverter]::ToUInt64($vbytes, $i * 8)) }
    $handlers = [ordered]@{}
    foreach ($i in 8..12) {
        $addr = [BitConverter]::ToUInt64($vbytes, $i * 8)
        $code = Read-Bytes $addr 0x600
        $handlers["slot$i"] = [ordered]@{ address = ("0x{0:X}" -f $addr); rva = ("0x{0:X}" -f ($addr - $base)); bytes = (Hex $code) }
        if ($null -ne $code) {
            for ($j = 0; $j -lt $code.Length - 5; $j++) {
                if ($code[$j] -eq 0xE8) {
                    $rel = [BitConverter]::ToInt32($code, $j + 1)
                    $t = [UInt64]([Int64]$addr + $j + 5 + $rel)
                    if ($t -gt $base -and $t -lt $base + 0x8000000) { $targets[$t] = $true }
                }
            }
        }
    }
    $dump.actions[$name] = [ordered]@{ vtable_rva = ("0x{0:X}" -f $Actions[$name]); slots = $slots; handlers = $handlers }
    Write-Host "  $name : ok"
}
if ($Extended) {
    # 3.1: the mission manager's own functions (its vtable is only known at run time): the
    # manager global at RVA 0x68DD510 -> object -> vtable; slots 0x120 (StartMissionAction calls
    # it) and 0x1E0 (the "finished" check), plus the ready check at RVA 0x1920740
    $mgrPtr = Read-Bytes ($base + 0x68DD510) 8
    $mm = [ordered]@{}
    if ($null -ne $mgrPtr) {
        $mgr = [BitConverter]::ToUInt64($mgrPtr, 0)
        $mm.manager = ("0x{0:X}" -f $mgr)
        if ($mgr -ne 0) {
            $head = Read-Bytes $mgr 0x40
            $mm.head = (Hex $head)
            if ($null -ne $head) {
                $vt = [BitConverter]::ToUInt64($head, 0)
                $mm.vtable_rva = ("0x{0:X}" -f ($vt - $base))
                $slots = Read-Bytes $vt (0x80 * 8)
                if ($null -ne $slots) {
                    $mm.slots = @()
                    for ($i = 0; $i -lt 0x80; $i++) { $mm.slots += ("0x{0:X}" -f ([BitConverter]::ToUInt64($slots, $i * 8) - $base)) }
                    foreach ($slot in @(0x120, 0x1E0, 0x118, 0x90)) {
                        $fn = [BitConverter]::ToUInt64($slots, $slot)
                        $mm[("slot_0x{0:X}" -f $slot)] = [ordered]@{ rva = ("0x{0:X}" -f ($fn - $base)); bytes = (Hex (Read-Bytes $fn 0x600)) }
                    }
                }
            }
        }
    }
    foreach ($rva in @(0x1920740, 0x19C8080, 0x19CD120, 0x19C90A0, 0x19CC980)) { $targets[$base + [UInt64]$rva] = $true }
    $dump.mission_manager = $mm
}
$n = 0
foreach ($t in ($targets.Keys | Sort-Object)) {
    if ($n -ge 400) { break }
    $dump.targets[("0x{0:X}" -f ($t - $base))] = (Hex (Read-Bytes $t 0x200))
    $n++
}
$dump | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Out -Encoding UTF8
Write-Host "written $Out ($n call targets). Send this file back."
