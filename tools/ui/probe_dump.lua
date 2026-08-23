-- probe_dump.lua v6 — everything into the persistent file channel.
local LOGPATH = "C:/Users/ivang/Documents/ArcheAge/ivanpanel_dump.txt"
local LOG = io.open(LOGPATH, "w")
local function L(s) if LOG then LOG:write(tostring(s) .. "\n") LOG:flush() end end

L("=== ivanpanel probe v6 ===")

-- 1. full global census
local sorted = {}
pcall(function()
    for k, v in pairs(_G) do sorted[#sorted + 1] = tostring(k) .. "\t" .. type(v) end
    table.sort(sorted)
end)
L("=== globals: " .. #sorted .. " ===")
for _, line in ipairs(sorted) do L("G " .. line) end

-- 2. widget internals
local winA = CreateEmptyWindow("ivanProbeA", "UIParent")
local winB = CreateEmptyWindow("ivanProbeB", "UIParent")

L("=== pairs(modalBackgroundWindow) ===")
local mbw = winA.modalBackgroundWindow
if type(mbw) == "table" then
    for k, v in pairs(mbw) do L(string.format("  [%s] <%s>", tostring(k), type(v))) end
end

-- 3. AddChild experiment
pcall(function() winA:AddChild(winB) end)
L("=== pairs(winA) tras AddChild ===")
for k, v in pairs(winA) do L(string.format("  [%s] %s <%s>", tostring(k), tostring(v):sub(1, 30), type(v))) end
L("=== pairs(winB) tras AddChild ===")
for k, v in pairs(winB) do L(string.format("  [%s] %s <%s>", tostring(k), tostring(v):sub(1, 30), type(v))) end

-- 4. getters sanity
for _, m in ipairs({ "GetId", "GetText", "GetOffset", "GetExtent", "GetWidth",
                     "GetHeight", "GetEffectiveOffset", "GetParent", "IsVisible" }) do
    local ok, r = pcall(function() return winA[m](winA) end)
    L("GET " .. m .. " => " .. (ok and tostring(r) or "ERR"))
end

-- 5. hunt for existing window registries among global tables
L("=== globals que parecen registros de ventanas ===")
pcall(function()
    for k, v in pairs(_G) do
        if type(v) == "table" and type(v.AddChild) == "function" then
            L("  REG? " .. tostring(k))
        end
    end
end)

L("=== v6 end ===")
if LOG then LOG:close() end
