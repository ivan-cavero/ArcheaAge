-- probe_dump.lua v9 — GetAddonInfos deep-dive + CreateTopLevelWidget signatures
local LOGPATH = "C:/Users/ivang/Documents/ArcheAge/ivanpanel_dump.txt"
local LOG = io.open(LOGPATH, "w")
local function L(s) if LOG then LOG:write(tostring(s) .. "\n"); LOG:flush() end end

-- 1. GetAddonInfos full dump
L("=== GetAddonInfos ===")
local infos = nil
pcall(function() infos = ADDON.GetAddonInfos() end)
if type(infos) == "table" then
    L("  entries=" .. #infos)
    for i, entry in ipairs(infos) do
        L(string.format("  [%d] <%s>", i, type(entry)))
        if type(entry) == "table" then
            for k, v in pairs(entry) do
                L(string.format("      %s = %s <%s>", tostring(k), tostring(v):sub(1, 50), type(v)))
            end
        end
    end
end

-- 2. CreateTopLevelWidget signature variants
local function tryCreate(desc, fn)
    local ok, r = pcall(fn)
    if ok and r ~= nil then
        L("OK " .. desc .. " -> <" .. type(r) .. ">")
        return r
    end
    L("-- " .. desc .. " -> " .. tostring(r))
    return nil
end

local w = tryCreate("CTLW(2 args)", function() return ADDON.CreateTopLevelWidget("ivanpanel", "IVANTEST") end)
    or tryCreate("CTLW(name,id)", function() return ADDON.CreateTopLevelWidget("IVANPANEL", "IVANTEST") end)
    or tryCreate("CTLW(3 args)", function() return ADDON.CreateTopLevelWidget("ivanpanel", "IVANTEST", 0) end)

-- 3. if any variant worked, finish building the test widget
if w ~= nil then
    L("=== widget creado via ADDON ===")
    pcall(function()
        for k, v in pairs(w) do L(string.format("  [%s] <%s>", tostring(k), type(v))) end
        w:SetExtent(240, 80)
        w:AddAnchor("CENTER", "UIParent", 0, -100)
        w:Show(true)
        local lblw = w:CreateChildWidget("label", "ivanTlLbl", 0, true)
        lblw:SetText("TOPLEVEL OK")
        L("  etiqueta TOPLEVEL OK colocada al centro")
    end)
else
    L("ninguna firma funcionó — se requiere registro previo del addon")
end

L("=== v9 end ===")
if LOG then LOG:close() end
