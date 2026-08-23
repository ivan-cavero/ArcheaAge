local LOG
pcall(function()
  LOG = io.open("../addon_aa_ui_log.txt", "w")
end)
if not LOG then
  pcall(function()
    LOG = io.open("addon_aa_ui_log.txt", "w")
  end)
end

local function L(s)
  if LOG then
    LOG:write(tostring(s) .. "\n")
    LOG:flush()
  end
end

L("=== aa_ui addon loaded ===")
L("CreateEmptyWindow: " .. tostring(CreateEmptyWindow))
L("UIParent: " .. tostring(UIParent))
L("CHAT_SYSTEM: " .. tostring(CHAT_SYSTEM))
L("X2LoginCharacter: " .. tostring(X2LoginCharacter))
pcall(function()
  CHAT_SYSTEM("aa_ui LOADED")
end)
local win
if CreateEmptyWindow then
  pcall(function()
    win = CreateEmptyWindow("aaUiWin", "UIParent")
    L("ventana via CreateEmptyWindow: " .. tostring(win))
  end)
end
if not win and UIParent then
  pcall(function()
    win = UIParent:CreateWidget("window", "aaUiWin", "UIParent")
    L("ventana via UIParent:CreateWidget: " .. tostring(win))
  end)
end
if win then
  pcall(function()
    win:Show(true)
    win:SetExtent(260, 140)
    win:AddAnchor("TOPRIGHT", "UIParent", -14, 70)
    
    local function lbl(id, text, dy, r, g, b)
      local l = win:CreateChildWidget("label", id, 0, true)
      l:SetAutoResize(true)
      l:SetText(text)
      if l.style and l.style.SetColor then
        l.style:SetColor(r, g, b, 1)
      end
      l:AddAnchor("TOPRIGHT", win, -8, dy)
      return l
    end
    
    lbl("ipTitle", "ArcheaAge", 6, 0.8, 0.89, 1)
    lbl("ipBy", "ArcheaAge Community", 32, 0.62, 0.72, 0.85)
    local total, limit = "?", "?"
    local ok1, v1 = pcall(function()
      return X2LoginCharacter:GetCurrentTotalCharactersCount()
    end)
    if ok1 and type(v1) == "number" then
      total = tostring(v1)
    end
    local ok2, v2 = pcall(function()
      return X2LoginCharacter:GetCurrentTotalCharactersLimit()
    end)
    if ok2 and type(v2) == "number" then
      limit = tostring(v2)
    end
    lbl("ipChars", "Personajes: " .. total .. " / " .. limit, 54, 0.62, 0.72, 0.85)
    lbl("ipBuild", "Build custom \194\183 preview UI", 76, 0.55, 0.65, 0.8)
    L("panel construido OK")
  end)
else
  L("NO se pudo crear ventana (ni CreateEmptyWindow ni UIParent)")
end
if LOG then
  LOG:close()
  LOG = nil
end
