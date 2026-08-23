backgroundWindow = CreateEmptyWindow("backgroundWindow", "UIParent")
backgroundWindow:AddAnchor("TOPLEFT", "UIParent", 0, 0)
backgroundWindow:AddAnchor("BOTTOMRIGHT", "UIParent", 0, 0)
backgroundWindow:Show(true)
local bgWindow = CreateLoginStageBgWindow(SERVER_SELECT_BG_PATH)
backgroundWindow.bgWindow = bgWindow
local mainWindow = backgroundWindow:CreateChildWidget("emptywidget", "centerWindow", 0, true)
mainWindow:AddAnchor("CENTER", backgroundWindow, 0, -60)
mainWindow:Show(true)
backgroundWindow.mainWindow = mainWindow
local title = backgroundWindow:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.IMG_TEXT, "background")
local coords = worldSelectLocale.titleCoords
title:SetExtent(coords[3], coords[4])
title:SetCoords(coords[1], coords[2], coords[3], coords[4])
title:AddAnchor("BOTTOM", mainWindow, "TOP", -20, -7)
local enterWorldBtn = backgroundWindow:CreateChildWidget("button", "enterWorldBtn", 0, true)
enterWorldBtn:Show(true)
enterWorldBtn:Enable(false)
enterWorldBtn:SetText(locale.server.enter)
enterWorldBtn.style:SetFont(FONT_PATH.DEFAULT, FONT_SIZE.XLARGE)
enterWorldBtn:AddAnchor("TOP", mainWindow, "BOTTOM", 0, 30)
enterWorldBtn:SetSounds("default")
ApplyButtonSkin(enterWorldBtn, BUTTON_LOGINSTAGE.MIX)
backgroundWindow.enterWorldBtn = enterWorldBtn
local refreshButton = backgroundWindow:CreateChildWidget("button", "refreshButton", 0, true)
refreshButton:AddAnchor("LEFT", title, "RIGHT", 3, 0)
ApplyButtonSkin(refreshButton, BUTTON_BASIC.RESET)
refreshButton:SetExtent(28, 27)
backgroundWindow.refreshButton = refreshButton

function CreateWorldList(id, parent, index, size)
  local widget = CreateScrollListCtrl(parent, id, index)
  widget:Show(true)
  widget:SetExtent(worldSelectLocale.worldList.extent[1], worldSelectLocale.worldList.extent[2])
  widget:AddAnchor("TOPLEFT", mainWindow, (widget.listCtrl:GetWidth() + 25) * (index - 1), 0)
  widget:SetUseDoubleClick(true)
  ChangeButtonSkin(widget.scroll.vs.thumb, BUTTON_BASIC.SERVER_SLIDER_VERTICAL_THUMB)
  widget.scroll:Show(false)
  local bg = CreateContentBackground(widget, "TYPE3")
  bg:AddAnchor("TOPLEFT", widget, -20, -20)
  bg:AddAnchor("BOTTOMRIGHT", widget, 15, 70)
  bg:SetColor(0, 0, 0, 0.2)
  
  local function ServerNameDataSetFunc(subItem, data, setValue)
    if setValue then
      subItem.nameLabel:SetText(data.name)
      if data.available then
        ApplyTextColor(subItem.nameLabel, FONT_COLOR.SOFT_YELLOW)
      else
        ApplyTextColor(subItem.nameLabel, FONT_COLOR.GRAY)
      end
    else
      subItem.nameLabel:SetText("")
    end
  end
  
  local function CharacterCountSetFunc(subItem, data, setValue, item)
    if setValue then
      if data > MAX_CHARACTER_COUNT then
        data = MAX_CHARACTER_COUNT
      end
      for i = 1, MAX_CHARACTER_COUNT do
        local icon = subItem.iconFrame.characerCountIcon[i]
        if i <= data then
          icon:AddAnchor("LEFT", subItem.iconFrame, (i - 1) * 14, 1)
        else
          icon:RemoveAllAnchors()
        end
        icon:SetVisible(i <= data)
      end
      subItem.iconFrame:SetWidth(data * 14)
      subItem.iconFrame:Show(data ~= 0)
    else
      subItem.iconFrame:SetWidth(0)
      subItem.iconFrame:Show(false)
    end
  end
  
  local function SetRaceCongestionIcon(icon, coords)
    icon:SetCoords(coords[1], coords[2], coords[3], coords[4])
    icon:SetExtent(coords[3], coords[4])
  end
  
  local function ServerStateSetFunc(subItem, data, setValue)
    if setValue then
      local coords = worldSelectLocale.worldList.raceCongestionIcon
      if data == RACE_CONGESTION.CHECK then
        SetRaceCongestionIcon(subItem.stateImage, coords.check)
      elseif data == RACE_CONGESTION.PRE_SELECT_RACE_FULL then
      elseif data == RACE_CONGESTION.FULL or data == RACE_CONGESTION.HIGH then
        SetRaceCongestionIcon(subItem.stateImage, coords.high)
      elseif data == RACE_CONGESTION.MIDDLE then
        SetRaceCongestionIcon(subItem.stateImage, coords.middle)
      elseif data == RACE_CONGESTION.LOW then
        SetRaceCongestionIcon(subItem.stateImage, coords.low)
      end
    else
      subItem:SetText("")
    end
  end
  
  local function RaceCreationImpossibilityDataSetFunc(subItem, data, setValue)
    if setValue then
      if data == nil then
        subItem.iconFrame:Show(false)
        return
      end
      subItem.iconFrame:Show(true)
      local iconVisibleCount = 1
      
      local function SetIcon(index, raceIndex)
        local coords = worldSelectLocale.worldList.raceTypeIcon[raceIndex]
        subItem.iconFrame.raceIcon[index]:SetVisible(true)
        subItem.iconFrame.raceIcon[index]:SetCoords(coords[1], coords[2], coords[3], coords[4])
        iconVisibleCount = iconVisibleCount + 1
      end
      
      for i = 1, #subItem.iconFrame.raceIcon do
        subItem.iconFrame.raceIcon[i]:SetVisible(false)
      end
      for i = 1, #RACE_TYPE do
        local race = RACE_TYPE[i]
        local str = X2Unit:GetRaceStr(race)
        if data[str] == RACE_CONGESTION.HIGH or data[str] == RACE_CONGESTION.FULL then
          SetIcon(iconVisibleCount, race)
        end
      end
      subItem.iconFrame:SetWidth((iconVisibleCount - 1) * 22)
    else
      subItem.iconFrame:Show(false)
    end
  end
  
  local function ServerListTooltipHandler(frame, subItem, rowIndex)
    if X2World:IsPreSelectCharacterPeriod() then
      return
    end
    
    local function GetRaceCongestionText(raceName, congestion)
      if congestion ~= RACE_CONGESTION.HIGH and congestion ~= RACE_CONGESTION.FULL then
        return ""
      end
      local index = GetRaceNameIndex(raceName)
      return string.format("%s%s %s", FONT_COLOR_HEX.RED, locale.raceText[index], locale.server.race_congestion_high)
    end
    
    function subItem:OnEnter()
      local data = frame:GetDataByViewIndex(rowIndex, 1)
      local race_tip = {}
      local tip = ""
      if data.available == true then
        for i = 1, #RACE_TYPE do
          local race = RACE_TYPE[i]
          local raceName = X2Unit:GetRaceStr(race)
          local congestion = data.raceCongestions[raceName]
          local str = string.format("%s", GetRaceCongestionText(raceName, congestion))
          if str ~= "" then
            tip = string.format("%s%s\n", tip, str)
          end
        end
        if tip ~= "" then
          if index == 1 then
            SetTargetAnchorTooltip(tip, "RIGHT", frame.listCtrl.items[rowIndex], "LEFT", 0, 0)
          else
            SetTargetAnchorTooltip(tip, "LEFT", frame.listCtrl.items[rowIndex], "RIGHT", 0, 0)
          end
        end
      end
    end
    
    subItem:SetHandler("OnEnter", subItem.OnEnter)
    
    function subItem:OnLeave()
      HideTooltip()
    end
    
    subItem:SetHandler("OnLeave", subItem.OnLeave)
  end
  
  local function ServerNameLayoutFunc(frame, rowIndex, colIndex, subItem)
    local nameLabel = subItem:CreateChildWidget("label", "nameLabel", 0, true)
    ApplyTextColor(nameLabel, FONT_COLOR.SOFT_YELLOW)
    nameLabel:Show(true)
    nameLabel:AddAnchor("LEFT", subItem, 20, 0)
    nameLabel.style:SetAlign(ALIGN_LEFT)
    nameLabel.style:SetShadow(true)
    subItem.nameLabel = nameLabel
    ServerListTooltipHandler(frame, subItem, rowIndex)
  end
  
  local function ServerStateLayoutFunc(frame, rowIndex, colIndex, subItem)
    local stateImage = subItem:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.IMG_TEXT, "background")
    stateImage:SetExtent(42, 21)
    stateImage:AddAnchor("CENTER", subItem, 0, 0)
    subItem.stateImage = stateImage
    ServerListTooltipHandler(frame, subItem, rowIndex)
  end
  
  local function CharacterCountLayoutFunc(frame, rowIndex, colIndex, subItem)
    local iconFrame = subItem:CreateChildWidget("emptywidget", "iconFrame", 0, true)
    iconFrame:Show(false)
    iconFrame:SetExtent(90, 22)
    iconFrame:AddAnchor("CENTER", subItem, 0, 0)
    iconFrame.characerCountIcon = {}
    for i = 1, MAX_CHARACTER_COUNT do
      local characerCountIcon = iconFrame:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.REMNANTS, "background")
      characerCountIcon:SetCoords(483, 445, 22, 24)
      characerCountIcon:SetExtent(20, 22)
      characerCountIcon:SetVisible(false)
      iconFrame.characerCountIcon[i] = characerCountIcon
    end
    ServerListTooltipHandler(frame, subItem, rowIndex)
  end
  
  local function RaceCreationImpossibilityLayoutFunc(frame, rowIndex, colIndex, subItem)
    local iconFrame = subItem:CreateChildWidget("emptywidget", "iconFrame", 0, true)
    iconFrame:Show(false)
    iconFrame:SetExtent(90, 21)
    iconFrame:AddAnchor("CENTER", subItem, 0, 0)
    iconFrame.raceIcon = {}
    for i = 1, #RACE_TYPE do
      local raceIcon = iconFrame:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.IMG_TEXT, "background")
      raceIcon:SetVisible(false)
      raceIcon:SetExtent(22, 21)
      raceIcon:AddAnchor("LEFT", iconFrame, (i - 1) * 22, 1)
      iconFrame.raceIcon[i] = raceIcon
    end
  end
  
  local columnWidth = worldSelectLocale.worldList.columnWidth
  widget:InsertColumn(locale.server.name, columnWidth[1], LCCIT_WINDOW, ServerNameDataSetFunc, nil, nil, ServerNameLayoutFunc, false)
  widget:InsertColumn(locale.server.character, columnWidth[2], LCCIT_WINDOW, CharacterCountSetFunc, nil, nil, CharacterCountLayoutFunc, false)
  widget:InsertColumn(locale.server.pre_select_cant_create, columnWidth[3], LCCIT_WINDOW, RaceCreationImpossibilityDataSetFunc, nil, nil, RaceCreationImpossibilityLayoutFunc, false)
  widget:InsertColumn(locale.server.state, columnWidth[4], LCCIT_WINDOW, ServerStateSetFunc, nil, nil, ServerStateLayoutFunc, false)
  widget.listCtrl.column[1].curSortFunc = nil
  widget.listCtrl.column[2].curSortFunc = nil
  widget.listCtrl.column[3].curSortFunc = nil
  widget.listCtrl.column[4].curSortFunc = nil
  
  function widget:SetRowCount(count)
    local preCount = self:GetRowCount()
    if count > preCount then
      self:InsertRows(count - preCount, false)
    end
    for i = 1, count do
      local item = self.listCtrl.items[i]
      if item.line == nil then
        local line = item:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.REMNANTS, "background")
        line:SetCoords(0, 293, 262, 3)
        line:SetColor(1, 1, 1, 0.15)
        line:SetHeight(3)
        line:AddAnchor("BOTTOMLEFT", item, 20, 2)
        line:AddAnchor("BOTTOMRIGHT", item, -20, 2)
        item.line = line
      end
    end
  end
  
  widget:SetRowCount(size)
  widget:SetColumnHeight(50)
  local title_bg = widget:CreateImageDrawable(LOGIN_STAGE_TEXTURE_PATH.REMNANTS, "background")
  if index == 1 then
    title_bg:SetCoords(290, 366, 380, 73)
    title_bg:AddAnchor("TOPLEFT", widget.listCtrl.column[1], -25, -15)
    title_bg:AddAnchor("BOTTOMRIGHT", widget.listCtrl.column[4], 20, 15)
  elseif index == 2 then
    title_bg:SetCoords(670, 366, -380, 73)
    title_bg:AddAnchor("TOPLEFT", widget.listCtrl.column[1], -5, -15)
    title_bg:AddAnchor("BOTTOMRIGHT", widget.listCtrl.column[4], 25, 15)
  end
  local inset = worldSelectLocale.worldList.columnInset
  for i = 1, #widget.listCtrl.column do
    widget.listCtrl.column[i]:SetInset(inset[1], inset[2], inset[3], inset[4])
    widget.listCtrl.column[i].style:SetFontSize(FONT_SIZE.XLARGE)
  end
  ListCtrlOverClickTextureSetting(widget.listCtrl)
  widget:ChangeSortMartTexture_serverSelectPage()
  return widget
end

local authMessage = CreateAuthMessageWindow(backgroundWindow)
authMessage:AddAnchor("TOP", backgroundWindow, 0, 200)
authMessage:SetExtent(250, 20)
backgroundWindow.authMessage = authMessage
local bottomPanel = CreateBottomPanel("bottomPanel", backgroundWindow)
local exitButton = CreateLoginStageExitButton("exitButton", bottomPanel)
backgroundWindow.bottomPanel = bottomPanel
backgroundWindow.exitButton = exitButton
local warningLabel = backgroundWindow:CreateChildWidget("textbox", "warningLabel", 0, true)
warningLabel:SetExtent(800, 20)
warningLabel:AddAnchor("BOTTOM", backgroundWindow, 0, -10)
warningLabel:SetLineSpace(3)
warningLabel.style:SetFontSize(FONT_SIZE.LARGE)
ApplyTextColor(warningLabel, FONT_COLOR.TITLE)
backgroundWindow.warningLabel = warningLabel

function CreateQueueWindow()
  local sideMargin, titleMargin, bottomMargin = GetWindowMargin()
  local window = CreateWindow("queueWindow", "UIParent")
  window:Show(false)
  window:SetExtent(POPUP_WINDOW_WIDTH, 185)
  window:AddAnchor("CENTER", "UIParent", 0, 0)
  window:SetUILayer("dialog")
  window:SetTitle(locale.server.titleWaitingToEnter)
  window.titleBar.closeButton:Show(false)
  window.titleBar:Clickable(false)
  window:SetWindowModal(true)
  local guideText = window:CreateChildWidget("label", "guideText", 0, true)
  guideText:SetExtent(0, 15)
  guideText:AddAnchor("TOP", window, 0, 45)
  guideText:AddAnchor("LEFT", window, 0, 0)
  guideText:AddAnchor("RIGHT", window, 0, 0)
  guideText:Show(true)
  guideText.style:SetFontSize(FONT_SIZE.MIDDLE)
  guideText.style:SetAlign(ALIGN_CENTER)
  ApplyTextColor(guideText, FONT_COLOR.DEFAULT)
  window.guideText = guideText
  local waitingQueueType = window:CreateChildWidget("label", "waitingQueueType", 0, true)
  waitingQueueType:SetExtent(0, 15)
  waitingQueueType:AddAnchor("TOP", guideText, "BOTTOM", 0, 15)
  waitingQueueType:AddAnchor("LEFT", window, 0, 0)
  waitingQueueType:AddAnchor("RIGHT", window, 0, 0)
  waitingQueueType.style:SetAlign(ALIGN_CENTER)
  waitingQueueType.style:SetFontSize(FONT_SIZE.LARGE)
  ApplyTextColor(waitingQueueType, FONT_COLOR.RED)
  waitingQueueType:Show(true)
  window.waitingQueueType = waitingQueueType
  local waitingLabel = window:CreateChildWidget("gametooltip", "waitingLabel", 0, true)
  waitingLabel:SetExtent(10, 15)
  waitingLabel:AddAnchor("TOP", waitingQueueType, "BOTTOM", 0, 5)
  waitingLabel:AddAnchor("LEFT", guideText, 0, 0)
  waitingLabel:AddAnchor("RIGHT", guideText, 0, 0)
  waitingLabel:SetInset(0, 0, 0, 0)
  ApplyTextColor(waitingLabel, FONT_COLOR.RED)
  waitingLabel.style:SetSnap(true)
  waitingLabel.style:SetFontSize(FONT_SIZE.LARGE)
  waitingLabel.style:SetAlign(ALIGN_CENTER)
  waitingLabel:Show(true)
  window.waitingLabel = waitingLabel
  local normalLengthLabel = window:CreateChildWidget("label", "normalLengthLabel", 0, true)
  normalLengthLabel:SetExtent(0, 15)
  normalLengthLabel:AddAnchor("TOP", waitingLabel, "BOTTOM", 0, 15)
  normalLengthLabel:AddAnchor("LEFT", window, 0, 0)
  normalLengthLabel:AddAnchor("RIGHT", window, 0, 0)
  normalLengthLabel.style:SetAlign(ALIGN_CENTER)
  normalLengthLabel.style:SetFontSize(FONT_SIZE.LARGE)
  ApplyTextColor(normalLengthLabel, FONT_COLOR.RED)
  normalLengthLabel:Show(true)
  window.normalLengthLabel = normalLengthLabel
  local premiumLengthLabel = window:CreateChildWidget("label", "premiumLengthLabel", 0, true)
  premiumLengthLabel:SetExtent(0, 15)
  premiumLengthLabel:AddAnchor("TOP", normalLengthLabel, "BOTTOM", 0, 5)
  premiumLengthLabel:AddAnchor("LEFT", window, 0, 0)
  premiumLengthLabel:AddAnchor("RIGHT", window, 0, 0)
  premiumLengthLabel.style:SetAlign(ALIGN_CENTER)
  premiumLengthLabel.style:SetFontSize(FONT_SIZE.LARGE)
  ApplyTextColor(premiumLengthLabel, FONT_COLOR.RED)
  premiumLengthLabel:Show(true)
  window.premiumLengthLabel = premiumLengthLabel
  local timeLabel = window:CreateChildWidget("label", "timeLabel", 0, true)
  timeLabel:SetExtent(0, 15)
  timeLabel:AddAnchor("TOP", premiumLengthLabel, "BOTTOM", 0, 5)
  timeLabel:AddAnchor("LEFT", window, 0, 0)
  timeLabel:AddAnchor("RIGHT", window, 0, 0)
  timeLabel.style:SetAlign(ALIGN_CENTER)
  timeLabel.style:SetFontSize(FONT_SIZE.LARGE)
  ApplyTextColor(timeLabel, FONT_COLOR.RED)
  timeLabel:Show(true)
  window.timeLabel = timeLabel
  local cancelBtn = window:CreateChildWidget("button", "cancel", 0, true)
  cancelBtn:AddAnchor("BOTTOM", window, -(BUTTON_COMMON_INSET.TWO_BUTTON_BETEEN + 5), BUTTON_COMMON_INSET.MESSAGEBOX_BOTTOM)
  ApplyButtonSkin(cancelBtn, BUTTON_BASIC.DEFAULT)
  cancelBtn:SetWidth(90)
  cancelBtn:SetText(locale.server.cancelWait)
  cancelBtn:Show(true)
  window.cancelBtn = cancelBtn
  local exitBtn = window:CreateChildWidget("button", "exit", 0, true)
  exitBtn:AddAnchor("BOTTOM", window, BUTTON_COMMON_INSET.TWO_BUTTON_BETEEN + 5, BUTTON_COMMON_INSET.MESSAGEBOX_BOTTOM)
  ApplyButtonSkin(exitBtn, BUTTON_BASIC.DEFAULT)
  exitBtn:SetWidth(90)
  exitBtn:SetText(locale.login.gameExit)
  exitBtn:Show(true)
  window.exitBtn = exitBtn
  
  function window:SetPremiumWainting(usePremium)
    if usePremium then
      waitingQueueType:Show(true)
      normalLengthLabel:Show(true)
      premiumLengthLabel:Show(true)
      waitingLabel:AddAnchor("TOP", waitingQueueType, "BOTTOM", 0, 5)
      timeLabel:AddAnchor("TOP", premiumLengthLabel, "BOTTOM", 0, 5)
      window:SetHeight(245)
    else
      waitingQueueType:Show(false)
      normalLengthLabel:Show(false)
      premiumLengthLabel:Show(false)
      waitingLabel:AddAnchor("TOP", guideText, "BOTTOM", 0, 15)
      timeLabel:AddAnchor("TOP", waitingLabel, "BOTTOM", 0, 5)
      window:SetHeight(185)
    end
  end
  
  return window
end

backgroundWindow.queueWindow = CreateQueueWindow()
if X2Debug:GetDevMode() then
  local zoneList = CreateVerticalStyleDropDown("worldSelectZoneList", backgroundWindow.mainWindow)
  zoneList:SetExtent(400, 60)
  zoneList:AddAnchor("TOPLEFT", "UIParent", "TOPLEFT", 10, 10)
  zoneList.nameButton:SetExtent(200, 30)
  zoneList.nameButton:AddAnchor("TOPLEFT", zoneList, "TOPLEFT", 0, 0)
  zoneList.nameButton:AddAnchor("BOTTOMRIGHT", zoneList, "BOTTOMRIGHT", 0, 0)
  zoneList.nameButton.style:SetFontSize(16)
  zoneList.listbox:SetExtent(0, 350)
  zoneList.listbox.list.itemStyle:SetFontSize(16)
  zoneList.listbox:SetUILayer("dialog")
  zoneList:Show(true)
  zoneList:AppendItem("--", -1)
  backgroundWindow.zoneList = zoneList
end
