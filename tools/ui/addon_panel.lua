-- addon_panel.lua — "ivanpanel": info panel on the world/server-select screen.
-- Hooked ONLY from loginstage/world_select/toc.g.
--
-- CONFIG: reads C:/Users/ivang/Documents/ArcheAge/ivanpanel_config.lua at load
-- (plain text, editable with notepad). Missing file -> built-in defaults.

-- ---- config loading -------------------------------------------------------
local CFG = {
    title     = "ArcheaAge",
    byline    = "Edited by Ivan Cavero",
    server    = "Servidor \194\183 EU-1",
    build     = "Build custom \194\183 preview UI",
    offset_x  = -18,
    offset_y  = 70,
    color_title = { 0.85, 0.78, 0.45 },
    color_text  = { 0.62, 0.72, 0.85 },
}
pcall(function()
    local f = io.open("C:/Users/ivang/Documents/ArcheAge/ivanpanel_config.lua", "r")
    if f then
        local body = f:read("*a") f:close()
        local fn = loadstring(body)
        if fn then
            local ok, userCfg = pcall(fn)
            if ok and type(userCfg) == "table" then
                for k, v in pairs(userCfg) do CFG[k] = v end
            end
        end
    end
end)

local function rgb(c) return c[1], c[2], c[3], c[4] or 1 end

-- ---- panel -----------------------------------------------------------------
local win = CreateEmptyWindow("ivanPanelWin", "UIParent")
win:Show(true)
win:SetExtent(280, 158)
win:AddAnchor("TOPRIGHT", "UIParent", CFG.offset_x, CFG.offset_y)

local function lbl(id, text, dy, color)
    local l = win:CreateChildWidget("label", id, 0, true)
    l:SetAutoResize(true)
    l:SetText(text)
    pcall(function() l.style:SetShadow(true) end)
    l.style:SetColor(rgb(color))
    l:AddAnchor("TOPRIGHT", win, -12, dy)
    return l
end

lbl("ipTitle", CFG.title,      6,   CFG.color_title)
lbl("ipBy",    CFG.byline,     34,  { 0.92, 0.92, 0.96 })
lbl("ipServer",CFG.server,     58,  CFG.color_text)

-- reserved slot: character count when the server sends it
local chars = lbl("ipChars", "", 82, CFG.color_text)

local live = lbl("ipLive",  "",             106, { 0.60, 0.78, 0.60 })
lbl("ipBuild", CFG.build,      130, { 0.55, 0.65, 0.80 })

-- ------------------------------------------------------------ live refresh --
local frames, tries = 0, 0
pcall(function()
    win:SetHandler("OnUpdate", function()
        frames = frames + 1
        if frames % 30 ~= 0 then return end            -- ~1 Hz

        local fps = nil
        pcall(function() fps = UIParent:GetFrameRate() end)
        local ok, hms = pcall(function() return os.date("%H:%M:%S") end)
        pcall(function()
            live:SetText(("FPS %d \194\183 %s"):format(fps or 0, ok and hms or ""))
        end)

        tries = tries + 1
        if tries <= 15 then                            -- char count grace window
            local okc, n = pcall(GetWorldCharacterCount)
            if okc and type(n) == "number" then
                pcall(function() chars:SetText(("Personajes: %d"):format(n)) end)
                tries = 999
            end
        end
    end)
end)
