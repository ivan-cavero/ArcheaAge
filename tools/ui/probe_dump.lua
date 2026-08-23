-- probe_dump.lua v11 — FULL recursive native widget tree -> tree.json
-- Children hang as fields on each window table (verified via decompiled
-- world_select.alb: backgroundWindow.mainWindow, .enterWorldBtn, ...).

local LOGPATH = "C:/Users/ivang/Documents/ArcheAge/game_ui_tree.json"
local LOG = io.open(LOGPATH, "w")
local function W(s) if LOG then LOG:write(s); LOG:flush() end end

local COUNT = 0
local SEEN = {}

local function isWidget(t)
    if type(t) ~= "table" then return false end
    -- our own windows store __this as a raw field
    local ok, r = pcall(function() return rawget(t, "__this") ~= nil end)
    if ok and r then return true end
    -- native windows expose methods through the metatable instead
    local okm, mt = pcall(getmetatable, t)
    if okm and type(mt) == "table" then
        local oki, idx = pcall(function() return mt.__index end)
        if oki and type(idx) == "table" and type(idx.AddChild) == "function" then
            return true
        end
        local oka, ac = pcall(function() return mt.AddChild end)
        if oka and type(ac) == "function" then return true end
    end
    return false
end

local function safeGet(o, m)
    local ok, r = pcall(function() return o[m] end)
    if ok then return r end
    return nil
end

local function emit(path, o, depth)
    COUNT = COUNT + 1
    local wid  = safeGet(o, "GetId")
    local wd   = safeGet(o, "GetWidth")
    local ht   = safeGet(o, "GetHeight")
    local vis  = safeGet(o, "IsVisible")
    local txt  = safeGet(o, "GetText")
    local off  = safeGet(o, "GetOffset")

    local jsep = (COUNT > 1) and "," or ""
    local escs = tostring(txt or ""):gsub('[%c"\\]', "")
    W(string.format('%s{"path":"%s","nativeId":%s,"w":%s,"h":%s,"visible":%s,"text":"%s"}\n',
        jsep, path,
        type(wid) == "number" and wid or "null",
        type(wd) == "number" and wd or "null",
        type(ht) == "number" and ht or "null",
        vis == false and "false" or "true",
        tostring(escs):sub(1, 60)))
end

local function walk(o, path, depth)
    if depth > 9 or COUNT > 2500 then return end
    if SEEN[o] then return end
    SEEN[o] = true

    emit(path, o, depth)

    for k, v in pairs(o) do
        if type(k) ~= "function" and isWidget(v) then
            walk(v, path .. "." .. tostring(k), depth + 1)
        elseif type(v) == "table" and not SEEN[v] then
            -- containers that hold widgets (e.g. worldList rows)
            for k2, v2 in pairs(v) do
                if isWidget(v2) then
                    walk(v2, path .. "." .. k .. "[" .. tostring(k2) .. "]", depth + 1)
                end
            end
        end
    end
end

W('{ "screen": "world_select", "widgets": [\n')

pcall(function()
    local roots = {}
    for k, v in pairs(_G) do
        if isWidget(v) then roots[#roots + 1] = { name = k, obj = v } end
    end
    table.sort(roots, function(a, b) return a.name < b.name end)
    for _, r in ipairs(roots) do
        walk(r.obj, r.name, 0)
    end
end)

W("\n] }")
if LOG then LOG:close() end
