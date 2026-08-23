-- probe_dump.lua v10 — export NATIVE top-level windows as tree.json
-- (the registry tables found in v6: every _G table exposing AddChild)
local LOGPATH = "C:/Users/ivang/Documents/ArcheAge/ivanpanel_tree.json"
local LOG = io.open(LOGPATH, "w")
local function FL() if LOG then LOG:flush() end end
local function L(s) if LOG then LOG:write(s); FL() end end

L('{ "screen": "world_select", "widgets": [')

local first = true
pcall(function()
    for k, v in pairs(_G) do
        if type(v) == "table" and type(v.AddChild) == "function" then
            local wid, off, wd, ht, vis = nil, nil, nil, nil, nil
            pcall(function() wid = tostring(v:GetId()) end)
            pcall(function() off = v:GetOffset() end)
            pcall(function() wd = v:GetWidth() end)
            pcall(function() ht = v:GetHeight() end)
            pcall(function() vis = v:IsVisible() end)

            local jsep = first and "" or ", "
            first = false
            L(string.format('%s{"id":"%s","nativeId":%s,"offset":%s,"w":%s,"h":%s,"visible":%s}',
                jsep, k,
                wid or "null",
                type(off) == "number" and off or "null",
                type(wd) == "number" and wd or "null",
                type(ht) == "number" and ht or "null",
                vis == false and "false" or "true"))
            FL()
        end
    end
end)

L("] }")
if LOG then LOG:close() end
