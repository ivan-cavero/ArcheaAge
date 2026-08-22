-- addon_panel.lua — "ivanpanel": info panel on the world/server-select screen.
-- Hooked ONLY from loginstage/world_select/toc.g (one module = one instance).
--
-- APIs proven present in this context (string tables of world_select_view.alb
-- / common.alb): CreateEmptyWindow, UIParent, win:CreateChildWidget,
-- style:SetColor, style:SetShadow, X2LoginCharacter.
-- Top-level errors surface in Documents/ArcheAge/ArcheAge.log.

local win = CreateEmptyWindow("ivanPanelWin", "UIParent")
win:Show(true)
win:SetExtent(260, 110)
win:AddAnchor("TOPRIGHT", "UIParent", -18, 84)

local function lbl(id, text, dy, r, g, b)
    local l = win:CreateChildWidget("label", id, 0, true)
    l:SetAutoResize(true)
    l:SetText(text)
    pcall(function() l.style:SetShadow(true) end)
    l.style:SetColor(r, g, b, 1)
    l:AddAnchor("TOPRIGHT", win, -10, dy)
    return l
end

lbl("ipTitle", "ArcheaAge", 6, 0.85, 0.78, 0.45)
lbl("ipBy",   "Edited by Ivan Cavero", 34, 0.92, 0.92, 0.96)

-- character count: only shown when the API actually returns numbers here
local function firstNumber(fns)
    for _, f in ipairs(fns) do
        local ok, v = pcall(f)
        if ok and type(v) == "number" then return v end
    end
    return nil
end

local total = firstNumber({
    function() return X2LoginCharacter:GetCurrentTotalCharactersCount() end,
    function() return X2LoginCharacter:GetTotalCharactersCount() end,
})
local limit = firstNumber({
    function() return X2LoginCharacter:GetCurrentTotalCharactersLimit() end,
})
if total and limit then
    lbl("ipChars", ("Personajes: %d / %d"):format(total, limit), 60, 0.62, 0.72, 0.85)
else
    lbl("ipServer", "Servidor \194\183 EU-1", 60, 0.62, 0.72, 0.85)
end

lbl("ipBuild", "Build custom \194\183 preview UI", 82, 0.55, 0.65, 0.80)
