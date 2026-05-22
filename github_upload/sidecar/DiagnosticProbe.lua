--[[
    DiagnosticProbe.lua — temporary v1.1 diagnostic for the
    Compatible Bodies Tooltip mod.

    Purpose:
      Probes the in-memory loca text for a hand-picked set of
      description handles at FOUR distinct lifecycle points,
      so we can see whether (a) our update is actually being
      applied for the FAILING handles, and (b) whether something
      overwrites it after we apply.

    Log prefix:
      All probe output is prefixed [CompatProbe] so it can be
      grep'd separately from the regular [AlanTooltipCompat] lines.

    Lifecycle stages:
      1. Module load          — baseline, before any event handlers
      2. StatsLoaded fired     — at the event tick our applyAll runs in
      3. +5 seconds after #2   — catches post-StatsLoaded overwrites
      4. GameState -> Running  — world fully loaded

    Edit PROBE_HANDLES if you want to track other items.

    Loaded by BootstrapClient.lua's trailing
        pcall(Ext.Require, "DiagnosticProbe")
    Remove (or run install_diagnostic_probe.bat --uninstall) to disable.
--]]

local PROBE_PREFIX = "[CompatProbe] "

local PROBE_HANDLES = {
    -- FAILING items (no compat shown in v1.0 ship as of 2026-05-20)
    { handle = "h3755e7c0g647fg4767g8796g34cb91a72a22", label = "FAIL ARM_ChainMail_1 (Chain Mail +1)" },
    { handle = "hf6c3324eg8adcg444dgb7d6g7fcb97dd1ea7", label = "FAIL ARM_ChainShirt_2 (Chain Shirt +2)" },
    { handle = "he001cf53g184bg49cbg8944gaac043b39925", label = "FAIL ARM_ChainShirt_Justiciar_Magic (Dark Justiciar Mail)" },
    -- WORKING items (compat shows correctly) for comparison
    { handle = "h974fb10dgea6fg4c58g949fga2122dc44753", label = "OK   ARM_Padded (parent of Padded +1/+2)" },
    { handle = "hd4386db1gb66ag4109gb956g649a51e6bba1", label = "OK   ARM_BreastPlate_1 (Breastplate +1)" },
    { handle = "hcfb32d30g6b95g466cg88cdg6d686e0c11ec", label = "OK   ARM_Splint_1 (Splint Armour +1)" },
}

local function p(line)
    Ext.Utils.Print(PROBE_PREFIX .. tostring(line))
end

local function probe(stage)
    p("===== STAGE: " .. stage .. " =====")
    for _, item in ipairs(PROBE_HANDLES) do
        local txt = Ext.Loca.GetTranslatedString(item.handle) or "<nil>"
        local has_marker = string.find(txt, "Compatible Bodies", 1, true) and "YES" or "NO "
        local tail = string.sub(txt, -70)
        tail = string.gsub(tail, "\n", "\\n")
        p(string.format("  marker=%s len=%4d  %s  tail=%q",
                        has_marker, string.len(txt), item.label, tail))
    end
    p("===== END STAGE: " .. stage .. " =====")
end

-- Stage 1: module load
probe("module load (Lua bootstrap running)")

-- Stage 2: StatsLoaded fires
Ext.Events.StatsLoaded:Subscribe(function()
    probe("StatsLoaded fired (subscribe order vs applyAll is undefined)")
end)

-- Stage 3: 5 seconds after StatsLoaded
local function scheduleStage3()
    local ok, err = pcall(function()
        Ext.Timer.WaitFor(5000, function()
            probe("5 seconds after StatsLoaded")
        end)
    end)
    if not ok then
        p("Ext.Timer.WaitFor unavailable: " .. tostring(err))
    end
end
Ext.Events.StatsLoaded:Subscribe(scheduleStage3)

-- Stage 4: GameStateChanged -> Running (world loaded)
local _stage4_done = false
Ext.Events.GameStateChanged:Subscribe(function(e)
    if _stage4_done then return end
    if e.ToState == "Running" then
        _stage4_done = true
        probe("GameState -> Running (world loaded)")
    end
end)

p("DiagnosticProbe registered (4 stages: module-load, StatsLoaded, +5s, world-loaded).")
