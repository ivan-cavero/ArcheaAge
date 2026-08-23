local sideMargin, titleMargin, bottomMargin = GetWindowMargin()
local gradeBgColor = {
  {
    187,
    147,
    149
  },
  {
    160,
    146,
    185
  },
  {
    137,
    179,
    198
  },
  {
    136,
    194,
    198
  },
  {
    170,
    197,
    135
  },
  {
    197,
    192,
    135
  },
  {
    226,
    188,
    105
  },
  {
    209,
    161,
    122
  }
}

function GetRemainTimeString(time)
  local tipText = locale.tooltip
  if time <= 0 then
    return ""
  end
  local sec = time % 60
  local totalMinute = math.floor(time / 60)
  local minute = totalMinute % 60
  local totalHour = math.floor(totalMinute / 60)
  local minute = totalMinute % 60
  local totalHour = math.floor(totalMinute / 60)
  local hour = totalHour % 24
  local day = math.floor(totalHour / 24)
  local str = ""
  if sec ~= 0 then
    str = string.format("%d%s", sec, tipText.second)
  end
  if minute ~= 0 then
    if 0 < string.len(str) then
      str = " " .. str
    end
    str = string.format("%d%s%s", minute, tipText.minute, str)
  end
  if hour ~= 0 then
    if 0 < string.len(str) then
      str = " " .. str
    end
    str = string.format("%d%s%s", hour, tipText.hour, str)
  end
  if day ~= 0 then
    if 0 < string.len(str) then
      str = " " .. str
    end
    str = string.format("%d%s%s", day, tipText.day, str)
  end
  str = locale.login.remainTime(str)
  return str
end

function AddEvent(widget)
  widget.deleteWaiting = false
  
  function widget:Init()
    widget.emptySlot = true
    widget.openBtn.infoLabel:SetText("")
    widget.openBtn.infoLabel.style:SetColor(0.3, 0.3, 0.3, 1)
    widget.closeBtn.infoLabel.style:SetColor(0.3, 0.3, 0.3, 1)
  end
  
  local delay = 300
  
  function widget:OnUpdate(dt)
    delay = delay + dt
    if 300 < delay then
      delay = 0
      local remain = X2LoginCharacter:GetCharacterDeleteWaitingTime(widget.index)
      if remain == nil then
        widget.deleteWaitingLabel:SetText("")
      else
        widget.deleteWaitingLabel:SetText(GetRemainTimeString(remain))
      end
    end
  end
  
  function widget:Update(name, job, level, seled, deleteWaiting)
    self.emptySlot = false
    local str = string.format("%s %s", X2Locale:LocalizeUiText(COMMON_TEXT, "character_level", tostring(level)), job)
    widget.openBtn:SetText(name)
    widget.openBtn.infoLabel:SetText(str)
    widget.closeBtn:SetText(name)
    widget.closeBtn.infoLabel:SetText(str)
    if seled == true then
      self.selected = true
    else
      self.selected = false
    end
    if deleteWaiting then
      widget.openBtn.infoLabel.style:SetColor(ConvertColor(144), ConvertColor(77), ConvertColor(77), 1)
      widget.closeBtn.infoLabel.style:SetColor(ConvertColor(144), ConvertColor(77), ConvertColor(77), 1)
      widget.deleteWaitingLabel:Show(true)
      widget:SetHandler("OnUpdate", widget.OnUpdate)
    else
      widget.openBtn.infoLabel.style:SetColor(0.3, 0.3, 0.3, 1)
      widget.closeBtn.infoLabel.style:SetColor(0.3, 0.3, 0.3, 1)
      widget.deleteWaitingLabel:Show(false)
      widget:ReleaseHandler("OnUpdate")
    end
    self.deleteWaiting = deleteWaiting
  end
end

function FindSelectedCharacterIdx()
  if charButtonList == nil then
    return nil
  end
  for i = 1, #charButtonList do
    if charButtonList[i].selected == true then
      return i
    end
  end
  return nil
end

local function CreateWorldQueueWindow(id, parent)
  local wnd = parent:CreateChildWidget("emptywidget", id, 0, true)
  wnd:SetExtent(1000, 100)
  wnd:AddAnchor("CENTER", parent, 0, -100)
  wnd:Clickable(false)
  local bg = wnd:CreateNinePartDrawable(LOGIN_STAGE_TEXTURE_PATH.QUEUE, "background")
  bg:SetCoords(0, 0, 512, 4)
  bg:SetInset(251, 2, 260, 1)
  bg:SetColor(0, ConvertColor(75), ConvertColor(155), 1)
  bg:AddAnchor("TOPLEFT", wnd, 0, 0)
  bg:AddAnchor("BOTTOMRIGHT", wnd, 0, 0)
  local userTypeText = wnd:CreateChildWidget("textbox", "userTypeText", 0, true)
  userTypeText:SetExtent(500, FONT_SIZE.XXLARGE)
  userTypeText:AddAnchor("TOP", wnd, 0, 25)
  userTypeText.style:SetAlign(ALIGN_CENTER)
  userTypeText.style:SetSnap(true)
  userTypeText.style:SetShadow(true)
  userTypeText.style:SetFontSize(FONT_SIZE.XXLARGE)
  ApplyTextColor(userTypeText, FONT_COLOR.FACTION_FRIENDLY_PC)
  local waitingText = wnd:CreateChildWidget("textbox", "waitingText", 0, true)
  waitingText:SetExtent(500, FONT_SIZE.XXLARGE)
  waitingText:AddAnchor("CENTER", wnd, 0, -15)
  waitingText.style:SetAlign(ALIGN_CENTER)
  waitingText.style:SetSnap(true)
  waitingText.style:SetShadow(true)
  waitingText.style:SetFontSize(FONT_SIZE.XXLARGE)
  ApplyTextColor(waitingText, FONT_COLOR.WHITE)
  local waitingRemain = wnd:CreateChildWidget("textbox", "waitingRemain", 0, true)
  waitingRemain:SetExtent(500, FONT_SIZE.XLARGE)
  waitingRemain:AddAnchor("TOP", waitingText, "BOTTOM", 0, sideMargin / 2)
  waitingRemain:SetLineSpace(TEXTBOX_LINE_SPACE.MIDDLE)
  waitingRemain.style:SetAlign(ALIGN_CENTER)
  waitingRemain.style:SetSnap(true)
  waitingRemain.style:SetShadow(true)
  waitingRemain.style:SetFontSize(FONT_SIZE.XLARGE)
  ApplyTextColor(waitingRemain, FONT_COLOR.WHITE)
  local premiumLengthText = wnd:CreateChildWidget("textbox", "premiumLengthText", 0, true)
  premiumLengthText:SetExtent(500, FONT_SIZE.LARGE)
  premiumLengthText:AddAnchor("TOP", waitingRemain, "BOTTOM", 0, sideMargin)
  premiumLengthText.style:SetAlign(ALIGN_CENTER)
  premiumLengthText.style:SetSnap(true)
  premiumLengthText.style:SetShadow(true)
  premiumLengthText.style:SetFontSize(FONT_SIZE.LARGE)
  ApplyTextColor(premiumLengthText, FONT_COLOR.WHITE)
  local normalLengthText = wnd:CreateChildWidget("textbox", "normalLengthText", 0, true)
  normalLengthText:SetExtent(500, FONT_SIZE.LARGE)
  normalLengthText:AddAnchor("TOP", premiumLengthText, "BOTTOM", 0, sideMargin / 2)
  normalLengthText.style:SetAlign(ALIGN_CENTER)
  normalLengthText.style:SetSnap(true)
  normalLengthText.style:SetShadow(true)
  normalLengthText.style:SetFontSize(FONT_SIZE.LARGE)
  ApplyTextColor(normalLengthText, FONT_COLOR.WHITE)
  
  function wnd:UpdateWaitingInfo()
    local isPremiumUser = X2LoginCharacter:IsInPremiumQueue()
    local normalLength = X2LoginCharacter:GetWorldNormalQueueLength()
    local premiumLength = X2LoginCharacter:GetWorldPremiumQueueLength()
    local remainLength = X2LoginCharacter:GetWorldQueuePosition()
    local remainTime = X2LoginCharacter:GetWorldQueueExpectedTime()
    local premiumUserType = X2Locale:LocalizeUiText(COMMON_TEXT, "premiumUserType")
    local normalUserType = X2Locale:LocalizeUiText(COMMON_TEXT, "normalUserType")
    userTypeText:SetText(X2Locale:LocalizeUiText(COMMON_TEXT, "userTypeText", isPremiumUser and premiumUserType or normalUserType))
    local str = locale.characterSelect.waiting_entrance_text(string.format("%s%s|r", FONT_COLOR_HEX.ORANGE, tostring(remainLength)))
    waitingText:SetText(str)
    local timeStr
    if 0 < remainTime then
      local time = math.floor(remainTime / 60)
      local minute = time % 60
      time = math.floor(time / 60)
      local hour = time % 24
      time = math.floor(time / 24)
      local day = time
      local filter = FORMAT_FILTER.DAY + FORMAT_FILTER.HOUR + FORMAT_FILTER.MINUTE
      local tStr = locale.time.GetRemainDate(0, 0, day, hour, minute, 0, filter)
      timeStr = string.format("%s", locale.characterSelect.waiting_remainTime_text(string.format("%s%s|r", FONT_COLOR_HEX.ORANGE, tStr)))
    else
      timeStr = string.format("%s", locale.characterSelect.waiting_remainTime_calculating_text)
    end
    waitingRemain:SetText(timeStr)
    premiumLengthText:SetText(X2Locale:LocalizeUiText(COMMON_TEXT, "waitingUserCount", premiumUserType, string.format("|,%d;", premiumLength)))
    normalLengthText:SetText(X2Locale:LocalizeUiText(COMMON_TEXT, "waitingUserCount", normalUserType, string.format("|,%d;", normalLength)))
    local usePremium = X2LoginCharacter:UsePremiumEntrance()
    if usePremium then
      waitingText:SetHeight(FONT_SIZE.XLARGE)
      waitingText.style:SetFontSize(FONT_SIZE.XLARGE)
      waitingText:Show(true)
      waitingText:RemoveAllAnchors()
      waitingText:AddAnchor("TOP", userTypeText, "BOTTOM", 0, sideMargin)
      userTypeText:Show(true)
      waitingRemain:Show(true)
      premiumLengthText:Show(true)
      normalLengthText:Show(true)
      wnd:SetHeight(200)
    else
      waitingText:Show(true)
      waitingText:SetHeight(FONT_SIZE.XXLARGE)
      waitingText.style:SetFontSize(FONT_SIZE.XXLARGE)
      waitingText:RemoveAllAnchors()
      waitingText:AddAnchor("CENTER", wnd, 0, -15)
      userTypeText:Show(false)
      waitingRemain:Show(true)
      premiumLengthText:Show(false)
      normalLengthText:Show(false)
      wnd:SetHeight(100)
    end
  end
  
  return wnd
end

characterSelectWindow = CreateEmptyWindow("characterSelectWindow", "UIParent")
characterSelectWindow:Show(true)
characterSelectWindow:AddAnchor("TOPLEFT", "UIParent", "TOPLEFT", 0, 0)
characterSelectWindow:AddAnchor("BOTTOMRIGHT", "UIParent", "BOTTOMRIGHT", 0, 0)
characterSelectWindow:SetUILayer("game")
characterSelectWindow:Clickable(false)
characterSelectWindow.rightPanel = CreateEmptyWindow("characterSelectWindow.rightPanel", characterSelectWindow)
characterSelectWindow.rightPanel:Show(true)
characterSelectWindow.rightPanel:SetWidth(455)
characterSelectWindow.rightPanel:AddAnchor("TOPRIGHT", characterSelectWindow, 0, 0)
characterSelectWindow.rightPanel:AddAnchor("BOTTOMRIGHT", characterSelectWindow, 0, 0)
local rightPanel = characterSelectWindow.rightPanel
characterSelectWindow.bottomPanel = CreateBottomPanel("characterSelectWindow.bottomPanel", characterSelectWindow)
local bottomPanel = characterSelectWindow.bottomPanel
characterSelectWindow.bgWindow = CreateLoginStageBgWindow(CH_SELECT_BG_PATH)
characterSelectWindow.queueWindow = CreateWorldQueueWindow("queueWindow", characterSelectWindow)
characterSelectWindow.queueWindow:Clickable(false)
characterSelectWindow.queueWindow:Show(false)
local authMessage = CreateAuthMessageWindow(characterSelectWindow)
authMessage:AddAnchor("TOP", characterSelectWindow, 0, 200)
authMessage:SetExtent(250, 20)
characterSelectWindow.authMessage = authMessage
local selecteArcheAgeLogo = CreatePageTitleLogo("selecteArcheAgeLogo", characterSelectWindow, "selectPage")
local serverName = characterSelectWindow:CreateChildWidget("label", "serverName", 0, true)
serverName:SetExtent(100, FONT_SIZE.LARGE)
serverName:SetAlpha(0.7)
serverName:SetAutoResize(true)
serverName:SetText(X2World:GetCurrentWorldName())
serverName:AddAnchor("TOPLEFT", selecteArcheAgeLogo, "TOPRIGHT", 3, 3)
serverName.style:SetFont(FONT_PATH.SNAIL, FONT_SIZE.MIDDLE)
serverName.style:SetAlign(ALIGN_LEFT)
ApplyTextColor(serverName, FONT_COLOR.BLACK)
local textFrame = characterSelectWindow:CreateChildWidget("emptywidget", "textFrame", 0, true)
textFrame:Show(true)
textFrame:AddAnchor("TOP", characterSelectWindow, 0, sideMargin / 2)
textFrame:SetHeight(FONT_SIZE.LARGE)
local bmMileage = characterSelectWindow:CreateChildWidget("textbox", "bmMileage", 0, true)
bmMileage:SetHeight(FONT_SIZE.LARGE)
bmMileage:AddAnchor("LEFT", textFrame, 0, 0)
ApplyTextColor(bmMileage, FONT_COLOR.WHITE)
bmMileage.style:SetFont(FONT_PATH.SNAIL, FONT_SIZE.MIDDLE)
bmMileage.style:SetAlign(ALIGN_CENTER)
local laborpower_label = characterSelectWindow:CreateChildWidget("textbox", "laborpower_label", 0, true)
laborpower_label:SetHeight(FONT_SIZE.LARGE)
laborpower_label:AddAnchor("RIGHT", textFrame, 0, 0)
ApplyTextColor(laborpower_label, FONT_COLOR.WHITE)
laborpower_label.style:SetFont(FONT_PATH.SNAIL, FONT_SIZE.MIDDLE)
laborpower_label.style:SetAlign(ALIGN_CENTER)

function textFrame:SetValue(existCharacter)
  local laborpower_label = characterSelectWindow.laborpower_label
  local bmMileage = characterSelectWindow.bmMileage
  local inset = 0
  local laborPower = X2LoginCharacter:GetLoginCharacterLaborPower(1)
  local maxLaborPower = X2LoginCharacter:GetLoginCharacterMaxLaborPower(1)
  local mileage = X2LoginCharacter:GetLoginCharacterBmPoint(1)
  if not existCharacter then
    laborPower = 0
    maxLaborPower = 0
    mileage = 0
  end
  if not baselibLocale.useMileage then
    bmMileage:Show(false)
    bmMileage:SetWidth(0)
  else
    bmMileage:Show(true)
    bmMileage:SetWidth(500)
    bmMileage:SetText(string.format("%s |b%s;", locale.bmmileage.bmmileage, tostring(mileage)))
    bmMileage:SetWidth(bmMileage:GetLongestLineWidth() + 7)
    inset = sideMargin / 2
  end
  local laborText = characterSelectLocale.GetLaborPowerText(laborPower, maxLaborPower)
  laborpower_label:SetWidth(500)
  laborpower_label:SetText(laborText)
  laborpower_label:SetWidth(laborpower_label:GetLongestLineWidth() + 7)
  textFrame:SetWidth(laborpower_label:GetWidth() + bmMileage:GetWidth() + inset)
end

function CreatePremiumServiceGrade()
  local premiumLabel = characterSelectWindow:CreateChildWidget("label", "premiumLabel", 0, true)
  premiumLabel:SetAutoResize(true)
  premiumLabel:AddAnchor("TOP", characterSelectWindow, 20, sideMargin / 2 + 40)
  premiumLabel:SetHeight(FONT_SIZE.XXLARGE)
  premiumLabel.style:SetFont(FONT_PATH.SNAIL, FONT_SIZE.XXLARGE)
  premiumLabel.style:SetAlign(ALIGN_CENTER)
  local premiumBg = premiumLabel:CreateImageDrawable(TEXTURE_PATH.PREMIUM_SERVICE_LOGIN_STAGE_GRADE, "background")
  premiumBg:SetExtent(410, 90)
  premiumBg:AddAnchor("CENTER", premiumLabel, 0, 10)
  local grade = X2LoginCharacter:GetLoginCharacterPremiumGrade(1)
  local isPremiumService = X2PremiumService:IsPremiumService()
  local premiumIcon = characterSelectWindow:CreateImageDrawable(TEXTURE_PATH.PREMIUM_SERVICE_ICON, "overlay")
  premiumIcon:SetTextureInfo("icon_premium")
  premiumIcon:AddAnchor("RIGHT", premiumLabel, "LEFT", -3, -1)
  if grade == PG_PREMIUM_0 or isPremiumService == false then
    premiumLabel:Show(false)
    premiumBg:SetVisible(false)
    premiumIcon:SetVisible(false)
  else
    if baselibLocale.premiumService.usePremiumGrade then
      premiumLabel:SetText(locale.premium.premium_grade_num(tostring(grade - 1)))
    else
      premiumLabel:SetText(locale.premium.premium)
    end
    premiumLabel:Show(true)
    premiumBg:SetVisible(true)
    premiumIcon:SetVisible(true)
    premiumBg:SetColor(ConvertColor(gradeBgColor[grade - 1][1]), ConvertColor(gradeBgColor[grade - 1][2]), ConvertColor(gradeBgColor[grade - 1][3]), 1)
  end
end

if X2PremiumService:IsPremiumServiceEnable() then
  CreatePremiumServiceGrade()
else
  CreatePayFrame(characterSelectWindow, "horizon")
  characterSelectWindow.payFrame:AddAnchor("TOP", textFrame, "BOTTOM", 0, 6)
end

local function SetViewOfFolderButton(id, parent)
  local closeBtn = CreateEmptyButton(id .. "closeButton", parent)
  closeBtn:AddAnchor("TOPLEFT", parent, 0, 0)
  ApplyButtonSkinTable(closeBtn, BUTTON_LOGINSTAGE.CHAR_LIST_NUIAN_MALE)
  parent.closeBtn = closeBtn
  local infoLabel = CreateLabel(id .. ".closeBtn.infoLabel", closeBtn)
  infoLabel:Show(true)
  infoLabel:SetExtent(280, 22)
  infoLabel:AddAnchor("TOPLEFT", closeBtn, 105, 10)
  infoLabel.style:SetColor(0, 0, 0, 1)
  infoLabel.style:SetAlign(ALIGN_LEFT)
  closeBtn.infoLabel = infoLabel
  local openBtn = CreateEmptyButton(id .. "openBtn", parent)
  openBtn:AddAnchor("TOPLEFT", parent, 0, 0)
  ApplyButtonSkinTable(openBtn, BUTTON_LOGINSTAGE.CHAR_LIST_NUIAN_FEMALE)
  parent.openBtn = openBtn
  local infoLabel = CreateLabel(id .. ".openBtn.infoLabel", openBtn)
  infoLabel:Show(true)
  infoLabel:SetExtent(280, 22)
  infoLabel:AddAnchor("TOPLEFT", openBtn, 105, 10)
  infoLabel.style:SetAlign(ALIGN_LEFT)
  openBtn.infoLabel = infoLabel
  local deleteWaitingLabel = parent:CreateChildWidget("label", "deleteWaitingLabel", 0, true)
  deleteWaitingLabel:AddAnchor("BOTTOMLEFT", openBtn, "TOPLEFT", 100, -3)
  deleteWaitingLabel:AddAnchor("BOTTOMRIGHT", openBtn, "TOPRIGHT", 100, -3)
  ApplyTextColor(deleteWaitingLabel, FONT_COLOR.RED)
  deleteWaitingLabel.style:SetAlign(ALIGN_LEFT)
  deleteWaitingLabel:Show(false)
  local serverTransferIcon = parent:CreateChildWidget("emptywidget", "serverTransferIcon", 0, true)
  local coords = characterSelectLocale.serverTransferIcon.coords
  local anchor = characterSelectLocale.serverTransferIcon.anchor
  serverTransferIcon:Show(false)
  serverTransferIcon:SetExtent(coords[3], coords[4])
  serverTransferIcon:AddAnchor("BOTTOMLEFT", closeBtn, "TOPLEFT", anchor[1], anchor[2])
  local bg = serverTransferIcon:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.IMG_TEXT, "background")
  bg:AddAnchor("TOPLEFT", serverTransferIcon, 0, 0)
  bg:AddAnchor("BOTTOMRIGHT", serverTransferIcon, 0, 0)
  bg:SetCoords(coords[1], coords[2], coords[3], coords[4])
  
  local function OnEnter(self)
    SetTargetAnchorTooltip(X2Locale:LocalizeUiText(CHARACTER_SELECT_TEXT, "transfer_icon_tip"), "TOPLEFT", self, "TOPRIGHT", 2, -1)
  end
  
  serverTransferIcon:SetHandler("OnEnter", OnEnter)
  
  local function OnLeave()
    HideTooltip()
  end
  
  serverTransferIcon:SetHandler("OnLeave", OnLeave)
  return closeBtn, openBtn
end

local function GetCharacterZone(index)
  local zoneName = X2LoginCharacter:GetLoginCharacterZone(index)
  if zoneName == nil then
    zoneName = locale.unknown
  end
  return zoneName
end

function UpdateDetailCharacterInfo(widget, index)
  local factionName
  local chrFaction = X2LoginCharacter:GetLoginCharacterFaction(index)
  if chrFaction == nil then
    factionName = locale.characterSelect.invalidIndex
  else
    local factionInfo = X2Faction:GetFactionInfo(chrFaction)
    if factionInfo ~= nil then
      factionName = factionInfo.name or locale.unknown
    else
      factionName = X2LoginCharacter:GetLoginCharacterFactionName(index)
      if string.len(factionName) == 0 then
        factionName = locale.characterSelect.unknownFactionInfo .. "(" .. tostring(chrFaction) .. ")"
      end
    end
  end
  local zoneName = GetCharacterZone(index)
  if zoneName == nil then
    zoneName = "-"
  end
  local money = X2LoginCharacter:GetLoginCharacterMoney(index)
  local str = ""
  str = string.format("%s|m%s;", locale.characterSelect.availableMoney, money)
  str = string.format([[
%s
%s%s]], str, locale.characterSelect.faction, tostring(factionName))
  str = string.format([[
%s
%s%s]], str, locale.characterSelect.position, tostring(zoneName))
  if X2LoginCharacter:IsDeleteRequestedCharacter(index) then
    str = string.format([[
%s
%s%s]], str, FONT_COLOR_HEX.RED, X2Locale:LocalizeUiText(LOGIN_TEXT, "housing_authority_open"))
  end
  widget.textbox:SetText(str)
  widget.textbox:SetHeight(widget.textbox:GetTextHeight())
  local isUniverseLp = X2LoginCharacter:IsUniverseLp()
  if not isUniverseLp then
    local laborPower = X2LoginCharacter:GetLoginCharacterLaborPower(index)
    local maxLaborPower = X2LoginCharacter:GetLoginCharacterMaxLaborPower(index)
    local laborText = string.format("(%s%d|r/%d)", FONT_COLOR_HEX.BLUE, laborPower, maxLaborPower)
    widget.checkBox.textButton:SetText(tostring(locale.characterSelect.chargeLaborPower))
    widget.laborpower_textbox:SetText(laborText)
  end
  widget.checkBox:Show(not isUniverseLp)
  widget.laborpower_textbox:Show(not isUniverseLp)
end

local function CreateCharacterDetailWindow(id, parent)
  local window = UIParent:CreateWidget("emptywidget", id, parent)
  window:Show(true)
  local textbox = window:CreateChildWidget("textbox", "textbox", 0, true)
  textbox:SetWidth(388)
  textbox:SetInset(100, 0, 0, 0)
  textbox:SetLineSpace(TEXTBOX_LINE_SPACE.MIDDLE)
  textbox:AddAnchor("TOPLEFT", window, 0, 5)
  textbox.style:SetAlign(ALIGN_LEFT)
  ApplyTextColor(textbox, FONT_COLOR.BLACK)
  local checkBox = CreateCheckButton(id .. "lpManageCheck", window, locale.characterSelect.chargeLaborPower)
  checkBox:Show(true)
  checkBox:SetExtent(16, 16)
  checkBox:AddAnchor("BOTTOMLEFT", window, 100, -3)
  checkBox.style:SetAlign(ALIGN_LEFT)
  SetButtonFontColor(checkBox.textButton, GetBlackCheckButtonFontColor())
  window.checkBox = checkBox
  local laborpower_textbox = window:CreateChildWidget("textbox", "laborpower_textbox", 0, true)
  laborpower_textbox:SetExtent(100, 20)
  laborpower_textbox:AddAnchor("LEFT", checkBox.textButton, "RIGHT", 2, 0)
  ApplyTextColor(laborpower_textbox, FONT_COLOR.BLACK)
  laborpower_textbox.style:SetAlign(ALIGN_LEFT)
  
  function window.checkBox:CheckBtnCheckChagnedProc()
    local charIdx = FindSelectedCharacterIdx()
    if charIdx == nil or charIdx < 1 or 4 < charIdx then
      return
    end
    X2LoginCharacter:RequestLpManageCharacter(charIdx)
  end
  
  return window
end

local target = rightPanel

local function Setting_Widget_Tooltip_Handler(widget, index)
  function widget:OnEnter()
    if not self:IsEnabled() then
      if self.disableReason == DISALBE_REASON_LIMIT then
        SetTargetAnchorTooltip(locale.characterSelect.max_character_count_warning, "RIGHT", self, "LEFT", -5, 0)
        
        return
      elseif self.disableReason == DISALBE_REASON_LIMIT_BUT_EXPANDABLE then
        SetTargetAnchorTooltip(locale.characterSelect.max_character_count_warning2, "RIGHT", self, "LEFT", -5, 0)
        return
      end
      if X2LoginCharacter:IsInEnableStartingLocation(index) == false then
        SetTargetAnchorTooltip(locale.characterCreate.race_congestion_warning, "RIGHT", self, "LEFT", -5, 0)
      end
    end
  end
  
  widget:SetHandler("OnEnter", widget.OnEnter)
  
  function widget:OnLeave()
    HideTooltip()
  end
  
  widget:SetHandler("OnLeave", widget.OnLeave)
end

charButtonList = {}
DISALBE_REASON_NONE = 0
DISALBE_REASON_LIMIT = 1
DISALBE_REASON_LIMIT_BUT_EXPANDABLE = 2
for index = 1, MAX_CHARACTOR do
  local id = "charButtonList" .. index
  local widget = UIParent:CreateWidget("folder", id, rightPanel)
  widget:SetExtent(391, 88)
  if 1 < index then
    widget:AddAnchor("TOPLEFT", target, "BOTTOMLEFT", 0, 35)
  else
    widget:AddAnchor("TOPRIGHT", target, -15, 40)
  end
  local closeBtn, openBtn = SetViewOfFolderButton(id, widget)
  widget:SetOpenStateButton(closeBtn)
  widget:SetCloseStateButton(openBtn)
  widget:UseAnimation(true)
  widget:SetTitleHeight(70)
  widget:SetAnimateStep(1.5)
  if X2LoginCharacter:IsUniverseLp() then
    widget:SetExtendLength(70)
  else
    widget:SetExtendLength(80)
  end
  local detailInfo = CreateCharacterDetailWindow(id .. ".detailInfo", widget)
  widget:SetChildWidget(detailInfo)
  local width = 20
  local height = 29
  local aniWidget = CreateEmptyButton(id .. ".aniWidget", detailInfo)
  aniWidget:Show(true)
  aniWidget:SetExtent(width, height)
  aniWidget:AddAnchor("TOPRIGHT", widget, -20, 18)
  local aniTexture = aniWidget:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.REMNANTS, "background")
  aniTexture:SetColor(1, 1, 1, 1)
  aniTexture:SetCoords(118, 196, width, height)
  aniTexture:AddAnchor("TOPLEFT", aniWidget, 0, 3)
  aniTexture:AddAnchor("BOTTOMRIGHT", aniWidget, 0, 0)
  aniTexture:SetVisible(false)
  local selectedAnimation = {}
  for j = 1, 4 do
    selectedAnimation[j] = {}
  end
  local y = 196
  selectedAnimation[1].x = 118
  selectedAnimation[1].y = y
  selectedAnimation[1].w = width
  selectedAnimation[1].h = height
  selectedAnimation[1].time = 150
  selectedAnimation[1].scale = 1
  selectedAnimation[2].x = 139
  selectedAnimation[2].y = y
  selectedAnimation[2].w = width
  selectedAnimation[2].h = height
  selectedAnimation[2].time = 150
  selectedAnimation[2].scale = 1
  selectedAnimation[3].x = 160
  selectedAnimation[3].y = y
  selectedAnimation[3].w = width
  selectedAnimation[3].h = height
  selectedAnimation[3].time = 150
  selectedAnimation[3].scale = 1
  selectedAnimation[4].x = 139
  selectedAnimation[4].y = y
  selectedAnimation[4].w = width
  selectedAnimation[4].h = height
  selectedAnimation[4].time = 150
  selectedAnimation[4].scale = 1
  aniTexture:SetAnimFrameInfo(selectedAnimation)
  widget.aniTexture = aniTexture
  widget.closeBtn = closeBtn
  widget.closeBtn.disableReason = DISALBE_REASON_NONE
  widget.openBtn = openBtn
  widget.openBtn.disableReason = DISALBE_REASON_NONE
  widget.detailInfo = detailInfo
  widget.deleteButton = deleteButton
  widget.deleteWaitingBtn = deleteWaitingBtn
  widget.index = index
  widget.selected = false
  widget.emptySlot = false
  AddEvent(widget)
  widget:Init()
  target = widget
  Setting_Widget_Tooltip_Handler(widget.openBtn, index)
  Setting_Widget_Tooltip_Handler(widget.closeBtn, index)
  charButtonList[index] = widget
end
bottomPanelLeftButtons = {}
local exitButton = CreateLoginStageExitButton("exitButton", bottomPanel)
if characterSelectLocale.showReturnServer then
  local serverButton = bottomPanel:CreateChildWidget("button", "serverButton", 0, true)
  ApplyButtonSkinTable(serverButton, BUTTON_LOGINSTAGE.SERVER_SELECT)
  serverButton:Show(characterSelectLocale.showReturnServer)
  bottomPanel.serverButton = serverButton
  table.insert(bottomPanelLeftButtons, serverButton)
end
local optionButton = CreateLoingStageOptionButton("optionButton", bottomPanel)
bottomPanel.optionButton = optionButton
table.insert(bottomPanelLeftButtons, optionButton)
if ADDON:GetFeatureset() == true then
  local addonFrmae = CreateAddonFrame()
  local addonButton = bottomPanel:CreateChildWidget("button", "addonButton", 0, true)
  addonButton:AddAnchor("LEFT", optionButton, "RIGHT", 0, 1)
  ApplyButtonSkinTable(addonButton, BUTTON_LOGINSTAGE.UI_ADDON)
  
  function addonButton:OnClick()
    ToggleAddonFrame()
  end
  
  addonButton:SetHandler("OnClick", addonButton.OnClick)
  table.insert(bottomPanelLeftButtons, addonButton)
end
local deleteButton = bottomPanel:CreateChildWidget("button", "deleteButton", 0, true)
ApplyButtonSkinTable(deleteButton, BUTTON_LOGINSTAGE.CHARACTER_DELETE)
deleteButton.isDeleteBtn = true
table.insert(bottomPanelLeftButtons, deleteButton)
local deleteWaitingButton = bottomPanel:CreateChildWidget("button", "deleteWaitingButton", 0, true)
deleteWaitingButton:Show(false)
ApplyButtonSkinTable(deleteWaitingButton, BUTTON_LOGINSTAGE.CHARACTER_DELETE_CANCEL)
bottomPanel.staffButton = characterSelectLocale.CreateStaffButton(bottomPanel)
if bottomPanel.staffButton then
  table.insert(bottomPanelLeftButtons, bottomPanel.staffButton)
end
local startButton = bottomPanel:CreateChildWidget("button", "startButton", 0, true)
startButton:AddAnchor("BOTTOMRIGHT", bottomPanel, -10, 1)
startButton:SetSounds("default")
if X2World:IsPreSelectCharacterPeriod() then
  ApplyButtonSkinTable(startButton, BUTTON_LOGINSTAGE.RECUSTOMIZING)
else
  ApplyButtonSkinTable(startButton, BUTTON_LOGINSTAGE.GAME_START)
end
for i = 1, #bottomPanelLeftButtons do
  local button = bottomPanelLeftButtons[i]
  if i == 1 then
    button:AddAnchor("LEFT", exitButton, "RIGHT", 0, 1)
  else
    button:AddAnchor("LEFT", bottomPanelLeftButtons[i - 1], "RIGHT", 0, 1)
    if button.isDeleteBtn == true then
      deleteWaitingButton:AddAnchor("LEFT", bottomPanelLeftButtons[i - 1], "RIGHT", 0, 1)
    end
  end
end

function CreateInfoWindow(index, info)
  local infoWnd = characterSelectWindow:CreateChildWidget("window", "infoWindow", 0, true)
  infoWnd:SetExtent(1, 1)
  infoWnd:AddAnchor("CENTER", characterSelectWindow, 0, 0)
  infoWnd:Show(false)
  if info == nil then
    return
  end
  
  local function SetPostionOnBG(window, x, y)
    local centerX = 16144
    local centerY = 18313
    local width = 69810
    local height = 43651
    local bg_width = characterSelectWindow.bgWindow.bg:GetWidth()
    local bg_height = characterSelectWindow.bgWindow.bg:GetHeight()
    local posX = (x - centerX) / width * bg_width
    local posY = (centerY - y) / height * bg_height
    window:AddAnchor("CENTER", infoWnd, posX, posY)
    
    function window:ReAnchor()
      window:RemoveAllAnchors()
      window:AddAnchor("CENTER", infoWnd, CalcDontApplyUIScale(posX), CalcDontApplyUIScale(posY))
    end
  end
  
  local chWindow = infoWnd:CreateChildWidget("emptywidget", "chWindow", 0, true)
  chWindow:SetExtent(32, 32)
  
  function chWindow:OnEnter()
    local name = X2LoginCharacter:GetLoginCharacterName(index)
    local zone = GetCharacterZone(index)
    local text = tostring(name .. "\n" .. zone)
    SetTooltip(text, self)
  end
  
  chWindow:SetHandler("OnEnter", chWindow.OnEnter)
  
  function chWindow:OnLeave()
    HideTooltip()
  end
  
  chWindow:SetHandler("OnLeave", chWindow.OnLeave)
  local chDrawable = infoWnd:CreateImageDrawable("ui/map/icon/player_cursor.dds", "overlay")
  chDrawable:SetExtent(32, 32)
  chDrawable:SetCoords(0, 0, 32, 32)
  chDrawable:AddAnchor("CENTER", chWindow, 0, 0)
  local isShow = true
  if info.validCharPos == false then
    isShow = false
  else
    isShow = not info.inDirtyZone
  end
  SetPostionOnBG(chWindow, info.posX, info.posY)
  chWindow:Show(isShow)
  chDrawable:SetVisible(isShow)
  local hCount = info.houseCount
  local houseWnd = {}
  for i = 1, hCount do
    local hInfo = X2LoginCharacter:GetLoginCharacterInfoHouse(index, i)
    if hInfo then
      local hWindow = infoWnd:CreateChildWidget("emptywidget", "houseWindow" .. i, 0, true)
      hWindow:SetExtent(29, 27)
      
      function hWindow:OnEnter()
        local text = tostring(hInfo.name .. "\n" .. hInfo.zone)
        SetTooltip(text, self)
      end
      
      hWindow:SetHandler("OnEnter", hWindow.OnEnter)
      
      function hWindow:OnLeave()
        HideTooltip()
      end
      
      hWindow:SetHandler("OnLeave", hWindow.OnLeave)
      local hDrawable = infoWnd:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.REMNANTS, "artwork")
      if hInfo.type ~= nil then
        if hInfo.type == "farm" then
          hDrawable:SetCoords(119, 225, 29, 26)
          hDrawable:SetExtent(29, 26)
        elseif hInfo.type == "fishfarm" then
          hDrawable:SetCoords(148, 230, 27, 21)
          hDrawable:SetExtent(27, 21)
        else
          hDrawable:SetCoords(700, 138, 29, 22)
          hDrawable:SetExtent(29, 22)
        end
      end
      hDrawable:AddAnchor("CENTER", hWindow, 0, 0)
      SetPostionOnBG(hWindow, hInfo.x, hInfo.y)
      houseWnd[i] = hWindow
    end
  end
  infoWnd:EnableHidingIsRemove(true)
  
  function infoWnd:ReAnchorChildWnd()
    chWindow:ReAnchor()
    for i = 1, #houseWnd do
      houseWnd[i].ReAnchor()
    end
  end
  
  return infoWnd
end

function characterSelectWindow:UpdateUI_PreSelecteCharacterPeriod()
  if X2World:IsPreSelectCharacterPeriod() then
    self.bottomPanel.deleteButton:Enable(false)
    
    function deleteButton:OnEnter()
      if not self:IsEnabled() and X2World:IsPreSelectCharacterPeriod() then
        SetTargetAnchorTooltip(locale.server.pre_select_character_warning, "BOTTOMLEFT", self, "TOPLEFT", 0, 20)
      end
    end
    
    deleteButton:SetHandler("OnEnter", deleteButton.OnEnter)
    
    function deleteButton:OnLeave()
      HideTooltip()
    end
    
    deleteButton:SetHandler("OnLeave", deleteButton.OnLeave)
  end
end
