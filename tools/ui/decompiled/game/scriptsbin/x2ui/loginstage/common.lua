MAX_CHARACTOR = localeView.max_character_count

function RegistUIEvent(window, eventTable)
  for key, _ in pairs(eventTable) do
    window:RegisterEvent(key)
  end
end

function CreateAuthMessageWindow(parent)
  local authMessage = parent:CreateChildWidget("textbox", "authMessage", 0, true)
  authMessage:Show(false)
  authMessage:SetWidth(300)
  authMessage:AddAnchor("TOPLEFT", "UIParent", 0, 58)
  authMessage:SetInset(15, 0, 0, 0)
  authMessage:SetLineSpace(TEXTBOX_LINE_SPACE.MIDDLE)
  authMessage.style:SetFont(FONT_PATH.DEFAULT, FONT_SIZE.LARGE)
  authMessage.style:SetAlign(ALIGN_LEFT)
  ApplyTextColor(authMessage, FONT_COLOR.NOTICE_ORANGE)
  local bg = authMessage:CreateImageDrawable(TEXTURE_PATH.DEFAULT, "background")
  bg:SetColor(0, 0, 0, 0.4)
  bg:SetCoords(469, 406, 215, 168)
  bg:AddAnchor("TOPLEFT", authMessage, 0, -10)
  bg:AddAnchor("BOTTOMRIGHT", authMessage, 60, 10)
  local fadeInTime = 1000
  local fadeOutTime = 1000
  
  function authMessage:SetMessage(msg, remainTime)
    authMessage:SetText(msg)
    authMessage:SetHeight(authMessage:GetTextHeight() + 10)
    if 0 < remainTime then
      authMessage:Show(true, fadeInTime)
      authMessage:Raise()
    else
      authMessage:Show(false, fadeOutTime)
    end
  end
  
  local evnets = {
    NOTIFY_AUTH_FATIGUE_MESSAGE = function(msg, remainTime)
      authMessage:SetMessage(msg, remainTime)
    end,
    NOTIFY_AUTH_BILLING_MESSAGE = function(msg, remainTime)
      authMessage:SetMessage(msg, remainTime)
    end,
    NOTIFY_AUTH_ADVERTISING_MESSAGE = function(msg, remainTime)
      authMessage:SetMessage(msg, remainTime)
    end,
    NOTIFY_AUTH_NOTICE_MESSAGE = function(msg, remainTime)
      authMessage:SetMessage(msg, remainTime)
    end
  }
  authMessage:SetHandler("OnEvent", function(this, event, ...)
    evnets[event](...)
  end)
  RegistUIEvent(authMessage, evnets)
  return authMessage
end

local skillBtnPool = {}
local skillBtnPoolCount = 0

local function GetSkillButtonFromPool(parent)
  if skillBtnPool[parent] == nil then
    skillBtnPool[parent] = {}
  end
  local skillBtns = skillBtnPool[parent]
  local skillBtnCount = table.getn(skillBtns)
  local btn
  for _, existFld in pairs(skillBtns) do
    if existFld.isUsed == false then
      btn = existFld
      btn.isUsed = true
      break
    end
  end
  if btn == nil then
    skillBtnPoolCount = skillBtnPoolCount + 1
    local id = string.format("skillBtnPoolItem.%d", skillBtnPoolCount)
    btn = CreateSlotShapeButton("raceSkill" .. skillBtnPoolCount, parent)
    btn.isUsed = true
    table.insert(skillBtns, btn)
  end
  return btn
end

local function ResetSkillButtonPool()
  for _, skillBtn in pairs(skillBtnPool) do
    for _, btn in pairs(skillBtn) do
      if btn.isUsed == true then
        btn.isUsed = false
      end
      btn:RemoveAllAnchors()
      btn:Show(false)
    end
  end
end

local function SetTooltipSkillButton(button, info)
  local function OnEnter(self)
    ShowTooltip(info, self)
  end
  
  button:SetHandler("OnEnter", OnEnter)
end

MAX_CHARACTER_COUNT = 4
SCREEN_WIDTH = UIParent:GetScreenWidth()
SCREEN_HEIGHT = UIParent:GetScreenHeight()
BG_WIDTH = 1920
BG_HEIGHT = 1200
SERVER_SELECT_BG_PATH = "ui/login_stage/background/server_select_bg.dds"
CH_SELECT_BG_PATH = "ui/login_stage/background/ch_select_bg.dds"

function GetEnableCreateCharacter_PreSelectCharacterPeriod()
  if X2World:IsPreSelectCharacterPeriod() then
    if X2World:GetCurrentTotalCharactersCount() >= X2World:GetCurrentTotalCharactersLimit() then
      return false
    else
      return true
    end
  end
end

function GetEnableCreateCharacter_NotPreSelectCharacterPeriod()
  if not X2World:IsPreSelectCharacterPeriod() then
    if X2World:GetCurrentTotalCharactersCount() >= X2World:GetCurrentTotalCharactersLimit() then
      return false
    else
      return true
    end
  end
end

function GetEnableCreateCharacter_worldSelect()
  if X2World:GetTotalCharactersCount() >= X2World:GetCurrentTotalCharactersLimit() then
    return false
  else
    return true
  end
end

function GetRemainCreatableCharacterCount()
  return X2World:GetCurrentTotalCharactersLimit() - X2World:GetCurrentTotalCharactersCount()
end

RACE_CONGESTION = {
  LOW = 0,
  MIDDLE = 1,
  HIGH = 2,
  FULL = 3,
  PRE_SELECT_RACE_FULL = 9,
  CHECK = 10
}

function GetRaceCongestions()
  local race = X2:GetRaceCongestions()
  return race
end

function IsUnableRaceToCreate(index)
  local list = GetRaceCongestions()
  if index == nil then
    return false
  end
  if index < 1 or index > #list then
    return false
  end
  if list[index] == HIGH_CONGESTION or list[index] == FULL_CONGESTION then
    return true
  end
  return false
end

function IsUnableRaceToPlay(index)
  local list = GetRaceCongestions()
  if index == nil then
    return false
  end
  if index < 1 or index > #list then
    return false
  end
  if list[index] == MIDDLE_CONGESTION or list[index] == FULL_CONGESTION then
    return true
  end
  return false
end

FIGHT = 1
DEATH = 5
WILD = 6
MAGIC = 7
VOCATION = 8
LOVE = 10
ABILITY_TYPE = {
  FIGHT,
  MAGIC,
  WILD,
  LOVE,
  DEATH,
  VOCATION
}

function ABILITY_NAME(index)
  return locale.common.abilityCategoryName[index]
end

function ABILITY_TITLE(index)
  return GetCombinedAbilityName(index, 0, 0)
end

function ABILITY_DESC(index)
  return locale.characterCreate.abilityDesc[index]
end

ABILITY_SKILL = {
  [FIGHT] = {
    18132,
    10455,
    13282
  },
  [MAGIC] = {
    10752,
    11967,
    10664
  },
  [WILD] = {
    13564,
    13281,
    10708
  },
  [LOVE] = {
    10534,
    10546,
    10721
  },
  [DEATH] = {
    10201,
    11441,
    10434
  },
  [VOCATION] = {
    10481,
    12029,
    12075
  }
}
PHYSICAL = 1
MAGICAL = 2
PROTECT = 3
DEBUFF = 4
ENCHANT = 5
TENDENCY_TYPE = {
  PHYSICAL,
  MAGICAL,
  PROTECT,
  DEBUFF,
  ENCHANT
}
TENDENCY_NAME = {
  "physical_name",
  "magical_name",
  "protect_name",
  "debuff_name",
  "enchant_name"
}
TENDENCY_DESC = {
  "physicalAttack",
  "magicalAttack",
  "protect",
  "debuff",
  "enchant"
}
ABILITY_TENDENCY = {
  [FIGHT] = {
    3,
    1,
    2,
    3,
    3
  },
  [MAGIC] = {
    1,
    5,
    3,
    2,
    1
  },
  [WILD] = {
    5,
    2,
    1,
    2,
    2
  },
  [LOVE] = {
    1,
    2,
    5,
    2,
    2
  },
  [DEATH] = {
    1,
    4,
    2,
    3,
    2
  },
  [VOCATION] = {
    4,
    1,
    2,
    3,
    2
  }
}

function CreatePageTitleLogo(id, parent, style)
  local window = CreateEmptyWindow(id, parent)
  window:SetExtent(160, 60)
  window:AddAnchor("TOPLEFT", "UIParent", 11, 9)
  window:Show(true)
  local pageTitle = window:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.IMG_TEXT, "background")
  pageTitle:AddAnchor("TOPLEFT", window, 0, 0)
  pageTitle:AddAnchor("BOTTOMRIGHT", window, 0, 0)
  local coords
  if tostring(style) == "selectPage" then
    coords = loginStageCommonLocale.pageTitleCoords.selectCharacter
    window:SetExtent(coords[3], coords[4])
    pageTitle:SetCoords(coords[1], coords[2], coords[3], coords[4])
  elseif style == 1 then
    coords = loginStageCommonLocale.pageTitleCoords.createRace
    window:SetExtent(coords[3], coords[4])
    window:AddAnchor("TOPLEFT", "UIParent", 10, 9)
    pageTitle:SetCoords(coords[1], coords[2], coords[3], coords[4])
  elseif style == 2 then
    coords = loginStageCommonLocale.pageTitleCoords.createCustomizing
    window:SetExtent(coords[3], coords[4])
    window:AddAnchor("TOPLEFT", "UIParent", 82, 9)
    pageTitle:SetCoords(coords[1], coords[2], coords[3], coords[4])
  elseif style == 3 then
    coords = loginStageCommonLocale.pageTitleCoords.createAbility
    window:SetExtent(coords[3], coords[4])
    pageTitle:SetCoords(coords[1], coords[2], coords[3], coords[4])
  end
  return window
end

function CreateLoginStageExitButton(id, parent)
  local exitButton = CreateEmptyButton(id, parent)
  exitButton:AddAnchor("BOTTOMLEFT", "UIParent", 0, 1)
  ApplyButtonSkinTable(exitButton, BUTTON_LOGINSTAGE.EXIT)
  
  function exitButton:OnClick(arg)
    if arg == "LeftButton" then
      Console:ExecuteString("quit")
    end
  end
  
  exitButton:SetHandler("OnClick", exitButton.OnClick)
  return exitButton
end

function CreateLoingStageOptionButton(id, parent)
  local optionButton = CreateEmptyButton(id, parent)
  ApplyButtonSkinTable(optionButton, BUTTON_LOGINSTAGE.OPTION)
  
  function optionButton:OnClick(arg)
    ToggleOptionFrame()
  end
  
  optionButton:SetHandler("OnClick", optionButton.OnClick)
  return optionButton
end

function CreateLoginStageBgWindow(path)
  if path == nil then
    return
  end
  local window = CreateEmptyWindow("bgWindow", "UIParent")
  window:SetExtent(UIParent:GetScreenWidth(), UIParent:GetScreenHeight())
  window:AddAnchor("CENTER", "UIParent", 0, 0)
  window:SetUILayer("background")
  window:Clickable(false)
  window.bg = window:CreateImageDrawable(path, "background")
  window.bg:SetCoords(0, 0, BG_WIDTH, BG_HEIGHT)
  if BG_WIDTH / BG_HEIGHT < SCREEN_WIDTH / SCREEN_HEIGHT then
    local new_height = math.floor(BG_HEIGHT * SCREEN_WIDTH / BG_WIDTH)
    window.bg:SetExtent(SCREEN_WIDTH, new_height)
  else
    local new_width = math.floor(BG_WIDTH * SCREEN_HEIGHT / BG_HEIGHT)
    window.bg:SetExtent(new_width, SCREEN_HEIGHT)
  end
  window.bg:AddAnchor("CENTER", window, 0, 0)
  window.bg:SetVisible(true)
  window:Show(true)
  
  function window:OnScale()
    if BG_WIDTH / BG_HEIGHT < SCREEN_WIDTH / SCREEN_HEIGHT then
      local new_height = math.floor(BG_HEIGHT * SCREEN_WIDTH / BG_WIDTH)
      window.bg:SetExtent(CalcDontApplyUIScale(SCREEN_WIDTH), CalcDontApplyUIScale(new_height))
    else
      local new_width = math.floor(BG_WIDTH * SCREEN_HEIGHT / BG_HEIGHT)
      window.bg:SetExtent(CalcDontApplyUIScale(new_width), CalcDontApplyUIScale(SCREEN_HEIGHT))
    end
  end
  
  window:SetHandler("OnScale", window.OnScale)
  return window
end

function CreateBottomPanel(id, parent)
  local widget = SetViewOfBottomPanel(id, parent)
  return widget
end

function SetViewOfBottomPanel(id, parent)
  local panel = CreateEmptyWindow(id, parent)
  panel:Show(true)
  panel:SetExtent(UIParent:GetScreenWidth(), 21)
  panel:AddAnchor("BOTTOMLEFT", parent, 0, 0)
  panel:AddAnchor("BOTTOMRIGHT", parent, 0, 0)
  panel:Raise()
  return panel
end

function CreateRightPanel(id, parent, step)
  local panel = CreateEmptyWindow(id, parent)
  panel:AddAnchor("TOPRIGHT", characterCreate.bgWindow, 0, 0)
  panel:AddAnchor("BOTTOMRIGHT", characterCreate.bgWindow, 0, 0)
  panel:Show(true)
  local archeAgeLogo = CreatePageTitleLogo(tostring(step) .. "archeAgeLogo", panel, step)
  return panel
end

FADE_IN_TIME = 300

function CreateLoginStageBlackWidnow(parent)
  local wnd = CreateEmptyWindow("loginStageBlackWnd", "UIParent")
  wnd.bg = wnd:CreateColorDrawable(0, 0, 0, 1, "background")
  wnd:Show(false)
  
  local function OnShow()
    wnd.bg:AddAnchor("TOPLEFT", "UIParent", 0, 0)
    wnd.bg:AddAnchor("BOTTOMRIGHT", "UIParent", 0, 0)
  end
  
  wnd:SetHandler("OnShow", OnShow)
  return wnd
end

local function CreateStaffWidnow()
  local staffWindow = CreateEmptyWindow("staffWindow", "UIParent")
  staffWindow:SetUILayer("system")
  staffWindow:Show(false)
  staffWindow.browser = staffWindow:CreateChildWidget("webbrowser", "webbrowser", 0, true)
  staffWindow.browser:AddAnchor("TOPLEFT", staffWindow, 0, 0)
  staffWindow.browser:AddAnchor("BOTTOMRIGHT", staffWindow, 0, 0)
  if staffWindow.browser.SetEscEvent then
    staffWindow.browser:SetEscEvent(true)
  end
  local returnButton = staffWindow:CreateChildWidget("button", "returnButton", 0, true)
  returnButton:SetText(locale.login.returnBtn)
  ApplyButtonSkin(returnButton, BUTTON_LOGINSTAGE.LOGIN)
  returnButton:AddAnchor("BOTTOMLEFT", staffWindow, 5, -5)
  returnButton.style:SetFontSize(FONT_SIZE.LARGE)
  returnButton:Show(true)
  
  function staffWindow:OnShow()
    StopMusic()
    X2LoginCharacter:StopLoginMovie()
    PlayMusic("login_stage_music_creator")
    staffWindow:RemoveAllAnchors()
    staffWindow:AddAnchor("TOPLEFT", "UIParent", 0, 0)
    staffWindow:AddAnchor("BOTTOMRIGHT", "UIParent", 0, 0)
    staffWindow.returnButton:AddAnchor("BOTTOMLEFT", staffWindow, "BOTTOMLEFT", 30, -5)
  end
  
  staffWindow:SetHandler("OnShow", staffWindow.OnShow)
  
  function staffWindow:OnEndFadeIn()
    staffWindow.browser:Show(true, FADE_IN_TIME)
    staffWindow.browser:SetURL("file:///" .. loginStageCommonLocale.made_html_path)
    staffWindow.browser:SetFocus(true)
  end
  
  staffWindow:SetHandler("OnEndFadeIn", staffWindow.OnEndFadeIn)
  
  function returnButton:OnClick(arg)
    if arg == "LeftButton" then
      ShowStaffWidnow(false)
    end
  end
  
  returnButton:SetHandler("OnClick", returnButton.OnClick)
  
  function staffWindow.browser:OnEndFadeOut()
    staffWindow:Show(false, FADE_IN_TIME)
  end
  
  staffWindow.browser:SetHandler("OnEndFadeOut", staffWindow.browser.OnEndFadeOut)
  
  function staffWindow:OnEndFadeOut()
    if staffWindow.hideFunc then
      staffWindow.hideFunc()
    end
  end
  
  staffWindow:SetHandler("OnEndFadeOut", staffWindow.OnEndFadeOut)
  return staffWindow
end

staffWindow = CreateStaffWidnow()
loginStageBlackWnd = CreateLoginStageBlackWidnow()

function SetShowHideFunctionForStaffWidnow(showFunc, hideFunc)
  staffWindow.showFunc = showFunc
  staffWindow.hideFunc = hideFunc
end

function ShowStaffWidnow(show)
  if show == true then
    if staffWindow.showFunc then
      staffWindow.showFunc()
    end
  else
    staffWindow.browser:Show(false, FADE_IN_TIME)
  end
end

function ShowRaceSkillButtons(parent, target, race, gender)
  ResetSkillButtonPool(parent)
  local count = X2Ability:GetRaceBuffCount(race, gender)
  local offset = 55
  for i = 1, count do
    local skillBtn = GetSkillButtonFromPool(parent)
    skillBtn:SetExtent(50, 50)
    local buffType = X2Ability:GetRaceBuffType(race, gender, i)
    local buffInfo = X2Ability:GetBuffTooltip(buffType, 1)
    skillBtn:SetIconPath(buffInfo.path)
    SetTooltipSkillButton(skillBtn, buffInfo)
    skillBtn:AddAnchor("TOPLEFT", target, "BOTTOMLEFT", i * offset - offset, 15)
    skillBtn:Show(true)
  end
end

function ClearSkillButtonPool(parent)
  ResetSkillButtonPool(parent)
end

function ShowAbilitySkillButtons(parent, target, index)
  ResetSkillButtonPool(parent)
  local ability = ABILITY_TYPE[index]
  local skillSet = ABILITY_SKILL[ability]
  local offset = 55
  for i = 1, #skillSet do
    local skillBtn = GetSkillButtonFromPool(parent)
    skillBtn:SetExtent(50, 50)
    local skillType = skillSet[i]
    local skillInfo = X2LoginCharacter:GetSkillTooltip(skillType, 0)
    skillBtn:SetIconPath(skillInfo.path)
    SetTooltipSkillButton(skillBtn, skillInfo)
    skillBtn:AddAnchor("TOPLEFT", target, "BOTTOMLEFT", i * offset - offset, 15)
    skillBtn:Show(true)
  end
end
