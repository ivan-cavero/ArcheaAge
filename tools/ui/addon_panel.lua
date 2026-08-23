-- addon_panel.lua — "ivanpanel": info panel on the world/server-select screen.
-- Hooked ONLY from loginstage/world_select/toc.g (one module = one instance).
--
-- Layout grid (TOPRIGHT stack, 22-26px pitch):
--   dy=6    ArcheaAge                    (title, gold)
--   dy=34   Edited by Ivan Cavero        (white)
--   dy=58   Servidor · EU-1              (static)
--   dy=82   Personajes: N                (reserved; filled if server sends it)
--   dy=106  FPS n · HH:MM:SS             (live, OnUpdate)
--   dy=130  Build custom · preview UI
--
-- Known crash rule: GetWorldCharacterCount() at module-load time crashes
-- natively — only call it from deferred handlers (OnUpdate) after login.

local win = CreateEmptyWindow("ivanPanelWin", "UIParent")
win:Show(true)
win:SetExtent(280, 158)
win:AddAnchor("TOPRIGHT", "UIParent", -18, 70)

local function lbl(id, text, dy, r, g, b)
    local l = win:CreateChildWidget("label", id, 0, true)
    l:SetAutoResize(true)
    l:SetText(text)
    pcall(function() l.style:SetShadow(true) end)
    l.style:SetColor(r, g, b, 1)
    l:AddAnchor("TOPRIGHT", win, -12, dy)
    return l
end

lbl("ipTitle", "ArcheaAge",                 6,   0.85, 0.78, 0.45)
lbl("ipBy",    "Edited by Ivan Cavero",     34,  0.92, 0.92, 0.96)
lbl("ipServer","Servidor \194\183 EU-1",   58,  0.62, 0.72, 0.85)

-- reserved slot for character count (filled by the live loop when available)
local chars = lbl("ipChars", "", 82, 0.75, 0.85, 0.95)
local live  = lbl("ipLive",  "", 106, 0.60, 0.78, 0.60)
lbl("ipBuild", "Build custom \194\183 preview UI", 130, 0.55, 0.65, 0.80)

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
        if tries <= 15 then                            -- char count: ~15 s de gracia
            local okc, n = pcall(GetWorldCharacterCount)
            if okc and type(n) == "number" then
                pcall(function() chars:SetText(("Personajes: %d"):format(n)) end)
                tries = 999                            -- conseguido: no reintentar
            end
        end
    end)
end)
