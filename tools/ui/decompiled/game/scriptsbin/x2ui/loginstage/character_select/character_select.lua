PlayMusic("login_stage_music_character_select")
local startButton = characterSelectWindow.bottomPanel.startButton
local optionButton = characterSelectWindow.bottomPanel.optionButton
local serverButton = characterSelectWindow.bottomPanel.serverButton
local deleteButton = characterSelectWindow.bottomPanel.deleteButton
local staffButton = characterSelectWindow.bottomPanel.staffButton
local deleteWaitingButton = characterSelectWindow.bottomPanel.deleteWaitingButton
local laborpower_label = characterSelectWindow.laborpower_label
local queueWindow = characterSelectWindow.queueWindow
local initCharIndex = X2LoginCharacter:GetLastPlayedCharacterIndex()
if initCharIndex == nil or initCharIndex > MAX_CHARACTOR then
  initCharIndex = 1
end

local function SelectedReanchor(selIndex)
  for i = 1, MAX_CHARACTOR do
    charButtonList[i]:RemoveAllAnchors()
  end
  local xOffset = 0
  for i = 1, MAX_CHARACTOR do
    if i == selIndex then
      xOffset = -45
    elseif i == selIndex + 1 then
      if selIndex == 1 then
        xOffset = 30
      else
        xOffset = 45
      end
    elseif i == 1 then
      xOffset = -15
    else
      xOffset = 0
    end
    if i == 1 then
      charButtonList[i]:AddAnchor("TOPRIGHT", characterSelectWindow.rightPanel, xOffset, 40)
    else
      charButtonList[i]:AddAnchor("TOPLEFT", charButtonList[i - 1], "BOTTOMLEFT", xOffset, 35)
    end
  end
end

local characterCount = X2LoginCharacter:GetNumLoginCharacters()
if characterCount ~= 0 then
  X2LoginCharacter:ShowSelectedCharacter(initCharIndex)
  charButtonList[initCharIndex]:OpenFolder()
  charButtonList[initCharIndex].aniTexture:Animation(true, true)
  SelectedReanchor(initCharIndex)
else
  initCharIndex = 0
end
local char_selIndex
local initialInput = true

local function IsDeleteRequestedCharacter(index)
  return X2LoginCharacter:IsDeleteRequestedCharacter(index)
end

local function IsTransferRequestedCharacter(index)
  return X2LoginCharacter:IsTransferRequestedCharacter(index)
end

characterSelectWindow.time = 0

function characterSelectWindow:OnUpdate(dt)
  self.time = dt + self.time
  if self.time > 15000 then
    X2LoginCharacter:RequestCharacterListRefresh(false)
    self.time = 0
  end
end

characterSelectWindow:SetHandler("OnUpdate", characterSelectWindow.OnUpdate)
local handledBtn

local function SetButtonHandler(button, text)
  handledBtn = button
  local delay = 0
  local cnt = -1
  
  function handledBtn:OnUpdate(dt)
    delay = delay - dt
    if delay < 0 then
      delay = 500
      cnt = (cnt + 1) % 4
      local str = text
      for i = 1, cnt do
        str = str .. "."
      end
      handledBtn:SetText(str)
    end
  end
  
  handledBtn:SetHandler("OnUpdate", handledBtn.OnUpdate)
end

local function ReleaseButtonHandler()
  if handledBtn ~= nil then
    handledBtn:ReleaseHandler("OnUpdate")
    handledBtn = nil
  end
end

local isReadyToSelectCharacter = true

local function SetReadyToSelectCharacter(isReady, isStart)
  isReadyToSelectCharacter = isReady
  deleteButton:Enable(isReady and char_selIndex ~= nil)
  deleteWaitingButton:Enable(isReady and char_selIndex ~= nil)
  optionButton:Enable(isReady)
  if serverButton then
    serverButton:Enable(isReady)
  end
  if isReady then
    ReleaseButtonHandler()
    startButton:SetText("")
    if X2LoginCharacter:GetWorldQueuePosition() > 0 then
      startButton:Enable(false)
    elseif char_selIndex ~= nil and not IsDeleteRequestedCharacter(char_selIndex) then
      startButton:Enable(true)
    else
      startButton:Enable(false)
    end
    if X2World:IsPreSelectCharacterPeriod() then
      ChangeButtonSkinTable(startButton, BUTTON_LOGINSTAGE.RECUSTOMIZING)
    else
      ChangeButtonSkinTable(startButton, BUTTON_LOGINSTAGE.GAME_START)
    end
    characterSelectWindow:SetHandler("OnUpdate", characterSelectWindow.OnUpdate)
  else
    ToggleOptionFrame(false)
    startButton:Enable(false)
    if isStart ~= nil and isStart then
      SetButtonHandler(startButton, locale.login.connecting)
      ChangeButtonSkinTable(startButton, BUTTON_LOGINSTAGE.WAITING_TO_START)
      SetButtonFontColor(startButton, GetLoginStageWaitingFontColor())
      startButton.style:SetAlign(ALIGN_LEFT)
      startButton:SetInset(100, 50, 0, 0)
      startButton.style:SetSnap(true)
      startButton.style:SetShadow(false)
      startButton.style:SetFont(FONT_PATH.SNAIL, 24)
    end
    characterSelectWindow:ReleaseHandler("OnUpdate")
  end
  UpateList_Enable()
end

local function ProcStartGame(skipClientDriven)
  if skipClientDriven == nil then
    skipClientDriven = false
  end
  local result = X2LoginCharacter:SelectCharacter(char_selIndex, skipClientDriven)
  if result == true then
    StopMusic()
    PlayUISound("login_stage_start_game")
    SetReadyToSelectCharacter(false, true)
  end
end

local function SelectCharacter()
  if X2World:IsPreSelectCharacterPeriod() then
    X2LoginCharacter:EditCharacter(char_selIndex)
  elseif X2LoginCharacter:CanShowClientDrivenSkipDialog(char_selIndex) then
    local function DialogHandler(wnd)
      wnd:SetTitle(X2Locale:LocalizeUiText(MSG_BOX_TITLE_TEXT, "error_message"))
      
      wnd:SetContent(GetCommonText("client_driven_skip_enable_msg"))
      wnd.btnOk:SetText(GetCommonText("client_driven_continue"))
      wnd.btnCancel:SetText(GetCommonText("client_driven_skip"))
      wnd.titleBar.closeButton:Show(false)
      
      function wnd:OkProc()
        ProcStartGame()
      end
      
      function wnd:CancelProc()
        ProcStartGame(true)
      end
    end
    
    X2DialogManager:RequestDefaultDialog(DialogHandler, characterSelectWindow:GetId())
  else
    ProcStartGame()
  end
end

local function ShowStaffWindow()
  SetReadyToSelectCharacter(false)
  loginStageBlackWnd:Show(true, FADE_IN_TIME)
  
  local function OnEndFadeIn()
    staffWindow:Show(true, FADE_IN_TIME)
  end
  
  loginStageBlackWnd:SetHandler("OnEndFadeIn", OnEndFadeIn)
end

local function HideStaffWindow()
  StopMusic()
  PlayMusic("login_stage_music_character_select")
  loginStageBlackWnd:Show(false, FADE_IN_TIME)
  SetReadyToSelectCharacter(true)
  X2LoginCharacter:RequestCharacterListRefresh(true)
end

if staffButton then
  function staffButton:OnClick(arg)
    if arg == "LeftButton" then
      SetShowHideFunctionForStaffWidnow(ShowStaffWindow, HideStaffWindow)
      
      ShowStaffWidnow(true)
    end
  end
  
  staffButton:SetHandler("OnClick", staffButton.OnClick)
end

local function ShowDeleteWaitingBtn(isWaiting)
  deleteButton:Show(not isWaiting)
  deleteWaitingButton:Show(isWaiting)
end

function deleteButton:OnClick(arg)
  if arg == "LeftButton" then
    if initialInput == true then
      X2Input:SetInputLanguage("Native")
      initialInput = false
    end
    ShowDeleteCharacter(characterSelectWindow, char_selIndex)
  end
end

deleteButton:SetHandler("OnClick", deleteButton.OnClick)

local function OnEnter(self)
  if self:IsEnabled() then
    return
  end
  if IsTransferRequestedCharacter(char_selIndex) then
    SetTargetAnchorTooltip(X2Locale:LocalizeUiText(CHARACTER_SELECT_TEXT, "delete_button_tip_transfer"), "BOTTOM", self, "TOP", 0, 15)
  end
end

deleteButton:SetHandler("OnEnter", OnEnter)

local function OnLeave()
  HideTooltip()
end

deleteButton:SetHandler("OnLeave", OnLeave)

function deleteWaitingButton:OnClick(arg)
  if arg == "LeftButton" then
    SetReadyToSelectCharacter(false)
    X2LoginCharacter:CancelCharacterDelete(char_selIndex)
  end
end

deleteWaitingButton:SetHandler("OnClick", deleteWaitingButton.OnClick)

local function SetFolderControlHandler(widget, folder, index, seleted)
  widget.folder = folder
  
  function widget:OnClick()
    if self.folder == nil then
      return
    end
    if self.folder:GetState() ~= "open" then
      if folder.emptySlot then
        X2LoginCharacter:CreateCharacter()
        return
      end
      UpdateList(index)
    elseif not X2LoginCharacter:IsDeleteRequestedCharacter(index) then
      SelectCharacter()
    end
    for i = 1, MAX_CHARACTOR do
      charButtonList[i].aniTexture:Animation(false, false)
      if i == index then
        charButtonList[i]:OpenFolder()
        charButtonList[i].aniTexture:Animation(true, true)
        SelectedReanchor(i)
      else
        charButtonList[i]:CloseFolder()
        charButtonList[i].aniTexture:Animation(false, false)
      end
    end
  end
  
  widget:SetHandler("OnClick", widget.OnClick)
end

for index = 1, MAX_CHARACTOR do
  local main = charButtonList[index]
  SetFolderControlHandler(main.closeBtn, main, index)
  SetFolderControlHandler(main.openBtn, main, index)
end
local charList_buttonStyleTable = {}
charList_buttonStyleTable[RACE_NUIAN] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_NUIAN_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_NUIAN_FEMALE
}
charList_buttonStyleTable[RACE_ELF] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_ELF_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_ELF_FEMALE
}
charList_buttonStyleTable[RACE_FERRE] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_FERE_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_FERE_FEMALE
}
charList_buttonStyleTable[RACE_HARIHARAN] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_HARIHARAN_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_HARIHARAN_FEMALE
}
charList_buttonStyleTable[RACE_DWARF] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_NUIAN_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_NUIAN_FEMALE
}
charList_buttonStyleTable[RACE_WARBORN] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_NUIAN_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_NUIAN_FEMALE
}
local charList_delete_buttonStyleTable = {}
charList_delete_buttonStyleTable[RACE_NUIAN] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_NUIAN_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_NUIAN_FEMALE
}
charList_delete_buttonStyleTable[RACE_ELF] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_ELF_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_ELF_FEMALE
}
charList_delete_buttonStyleTable[RACE_FERRE] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_FERE_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_FERE_FEMALE
}
charList_delete_buttonStyleTable[RACE_HARIHARAN] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_HARIHARAN_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_HARIHARAN_FEMALE
}
charList_delete_buttonStyleTable[RACE_DWARF] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_NUIAN_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_NUIAN_FEMALE
}
charList_delete_buttonStyleTable[RACE_WARBORN] = {
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_NUIAN_MALE,
  BUTTON_LOGINSTAGE.CHAR_LIST_DELETE_NUIAN_FEMALE
}
characterSelectLocale.AdjustLocaleButtonFont(charList_buttonStyleTable, charList_delete_buttonStyleTable, BUTTON_LOGINSTAGE.CHAR_LIST_CREATE)

local function ChangeCharListButtonStyle(button, raceName, gender, deleteWaiting)
  local raceIndex = GetRaceNameIndex(raceName)
  local genderIndex = GetGenderIndex(gender)
  if raceIndex == nil or genderIndex == nil then
    return
  end
  if deleteWaiting == true then
    ChangeButtonSkinTable(button, charList_delete_buttonStyleTable[raceIndex][genderIndex])
  else
    ChangeButtonSkinTable(button, charList_buttonStyleTable[raceIndex][genderIndex])
  end
end

local chInfoWindow

function UpateList_Enable()
  for i = 1, MAX_CHARACTOR do
    charButtonList[i].openBtn:Enable(isReadyToSelectCharacter)
    charButtonList[i].closeBtn:Enable(isReadyToSelectCharacter)
    if i > X2World:GetTotalCharactersDefaultLimit() + X2World:GetTotalCharactersExpandableLimit() then
      charButtonList[i]:Show(false)
    end
  end
  if not isReadyToSelectCharacter then
    return
  end
  local characterCount = X2LoginCharacter:GetNumLoginCharacters()
  characterCount = math.min(characterCount, MAX_CHARACTOR)
  if not X2World:IsPreSelectCharacterPeriod() then
    local remainCreatableCharacterCount = GetRemainCreatableCharacterCount()
    if not GetEnableCreateCharacter_NotPreSelectCharacterPeriod() then
      remainCreatableCharacterCount = 0
    end
    for i = characterCount + remainCreatableCharacterCount + 1, MAX_CHARACTOR do
      charButtonList[i].openBtn:Enable(false)
      charButtonList[i].closeBtn:Enable(false)
      local expandableCharacterCount = X2World:GetTotalCharactersExpandableLimit() - X2World:GetExpandedCharacterCount()
      if 0 < expandableCharacterCount then
        charButtonList[i].openBtn.disableReason = DISALBE_REASON_LIMIT_BUT_EXPANDABLE
        charButtonList[i].closeBtn.disableReason = DISALBE_REASON_LIMIT_BUT_EXPANDABLE
      else
        charButtonList[i].openBtn.disableReason = DISALBE_REASON_LIMIT
        charButtonList[i].closeBtn.disableReason = DISALBE_REASON_LIMIT
      end
    end
  end
  if not X2World:IsPreSelectCharacterPeriod() then
    for index = 1, math.min(characterCount, MAX_CHARACTOR) do
      local enable = X2LoginCharacter:IsInEnableStartingLocation(index)
      charButtonList[index].openBtn:Enable(enable)
      charButtonList[index].closeBtn:Enable(enable)
    end
  end
  characterSelectWindow:UpdateUI_PreSelecteCharacterPeriod()
  if not X2World:IsPreSelectCharacterPeriod() and char_selIndex ~= nil and char_selIndex ~= 0 then
    if not charButtonList[char_selIndex].openBtn:IsEnabled() or not charButtonList[char_selIndex].closeBtn:IsEnabled() then
      characterSelectWindow.bottomPanel.startButton:Enable(false)
    else
      local enable = not IsDeleteRequestedCharacter(char_selIndex)
      characterSelectWindow.bottomPanel.startButton:Enable(enable)
      if 0 < X2LoginCharacter:GetWorldQueuePosition() then
        characterSelectWindow.bottomPanel.startButton:Enable(false)
      end
      enable = not IsTransferRequestedCharacter(char_selIndex)
      characterSelectWindow.bottomPanel.deleteButton:Enable(enable)
    end
  end
end

function UpdateList(selIndex)
  local characterCount = X2LoginCharacter:GetNumLoginCharacters()
  characterCount = math.min(characterCount, MAX_CHARACTOR)
  for i = 1, MAX_CHARACTOR do
    charButtonList[i]:Init()
    charButtonList[i].openBtn:SetText(locale.characterSelect.create)
    charButtonList[i].serverTransferIcon:Show(false)
    ChangeButtonSkinTable(charButtonList[i].openBtn, BUTTON_LOGINSTAGE.CHAR_LIST_CREATE)
  end
  if characterCount ~= 0 and X2LoginCharacter:IsUniverseLp() then
    characterSelectWindow.textFrame:SetValue(true)
  else
    characterSelectWindow.textFrame:SetValue(false)
  end
  if X2PremiumService:IsPremiumServiceEnable() == false then
    characterSelectWindow.payFrame:SetValue()
  end
  for index = 1, math.min(characterCount, MAX_CHARACTOR) do
    local name = X2LoginCharacter:GetLoginCharacterName(index)
    local level = X2LoginCharacter:GetLoginCharacterLevel(index)
    local abilities = X2LoginCharacter:GetLoginCharacterAbilities(index)
    local job = GetCombinedAbilityName(abilities[1], abilities[2], abilities[3])
    local deleteWaiting = IsDeleteRequestedCharacter(index)
    local raceName = X2LoginCharacter:GetLoginCharacterRace(index)
    local gender = X2LoginCharacter:GetLoginCharacterGender(index)
    ChangeCharListButtonStyle(charButtonList[index].openBtn, raceName, gender, deleteWaiting)
    ChangeCharListButtonStyle(charButtonList[index].closeBtn, raceName, gender, deleteWaiting)
    UpdateDetailCharacterInfo(charButtonList[index].detailInfo, index)
    local enable = IsTransferRequestedCharacter(index)
    charButtonList[index].serverTransferIcon:Show(enable)
    if index == selIndex then
      if char_selIndex ~= index then
        char_selIndex = index
        X2LoginCharacter:ShowSelectedCharacter(index)
      end
      charButtonList[index]:Update(name, job, level, true, deleteWaiting)
    else
      charButtonList[index]:Update(name, job, level, false, deleteWaiting)
    end
    local triggerEvent = false
    if not X2LoginCharacter:IsUniverseLp() then
      local lpManagedCharIdx = X2LoginCharacter:GetLpManagedCharacterIdx()
      if lpManagedCharIdx == 0 then
        if X2LoginCharacter:GetLastPlayedCharacterIndex() ~= nil then
          lpManagedCharIdx = X2LoginCharacter:GetLastPlayedCharacterIndex()
        else
          lpManagedCharIdx = 1
        end
      end
      if index == lpManagedCharIdx then
        charButtonList[index].detailInfo.checkBox:SetChecked(true, triggerEvent)
        charButtonList[index].detailInfo.checkBox:SetEnableCheckButton(false)
      else
        charButtonList[index].detailInfo.checkBox:SetChecked(false, triggerEvent)
        charButtonList[index].detailInfo.checkBox:SetEnableCheckButton(true)
      end
      if deleteWaiting then
        charButtonList[index].detailInfo.checkBox:SetEnableCheckButton(false)
      end
    end
  end
  if selIndex == 0 or selIndex > characterCount then
    characterSelectWindow.bottomPanel.startButton:Enable(false)
    characterSelectWindow.bottomPanel.deleteButton:Enable(false)
  else
    local chInfo = X2LoginCharacter:GetLoginCharacterInfo(selIndex)
    if chInfoWindow ~= nil then
      chInfoWindow:Show(false, 500)
      chInfoWindow = nil
    end
    if chInfo ~= nil then
      chInfoWindow = CreateInfoWindow(selIndex, chInfo)
      chInfoWindow:Show(true, 500)
    end
    characterSelectWindow.bottomPanel.startButton:Enable(true)
    characterSelectWindow.bottomPanel.deleteButton:Enable(true)
  end
  UpateList_Enable()
  if selIndex ~= 0 then
    if not charButtonList[selIndex].openBtn:IsEnabled() or not charButtonList[selIndex].closeBtn:IsEnabled() then
      characterSelectWindow.bottomPanel.startButton:Enable(false)
    else
      local deleteWaiting = IsDeleteRequestedCharacter(selIndex)
      ShowDeleteWaitingBtn(deleteWaiting)
      characterSelectWindow.bottomPanel.startButton:Enable(not deleteWaiting)
    end
  end
  if 0 < X2LoginCharacter:GetWorldQueuePosition() then
    characterSelectWindow.bottomPanel.startButton:Enable(false)
  end
end

UpdateList(initCharIndex)
local startButton = characterSelectWindow.bottomPanel.startButton

function startButton:OnClick(arg)
  if arg == "LeftButton" then
    SelectCharacter()
  end
end

startButton:SetHandler("OnClick", startButton.OnClick)

local function LaborpowerLabelOnEnter(self)
  local str = locale.characterSelect.laborPowerTip(FONT_COLOR_HEX.ORANGE)
  SetTargetAnchorTooltip(str, "TOPLEFT", characterSelectWindow.textFrame, "BOTTOMRIGHT", -1, -3)
end

characterSelectWindow.textFrame:SetHandler("OnEnter", LaborpowerLabelOnEnter)
laborpower_label:SetHandler("OnEnter", LaborpowerLabelOnEnter)
characterSelectWindow.bmMileage:SetHandler("OnEnter", LaborpowerLabelOnEnter)

local function LaborpowerLabelOnLeave()
  HideTooltip()
end

characterSelectWindow.textFrame:SetHandler("OnLeave", LaborpowerLabelOnLeave)
laborpower_label:SetHandler("OnLeave", LaborpowerLabelOnLeave)
characterSelectWindow.bmMileage:SetHandler("OnLeave", LaborpowerLabelOnLeave)
local eventWnd = CreateEmptyWindow("eventWnd", "UIParent")
eventWnd:SetExtent(0, 0)
eventWnd:AddAnchor("TOPLEFT", "UIParent", 0, 0)
eventWnd:Show(true)

local function UpdateWorldEntranceWindow()
  local waitingLength = X2LoginCharacter:GetWorldQueuePosition()
  if 0 < waitingLength then
    queueWindow:UpdateWaitingInfo()
    queueWindow:Show(true)
  else
    queueWindow:Show(false)
  end
  UpateList_Enable()
end

UpdateWorldEntranceWindow()
local eventHandler = {
  LOGIN_CHARACTER_UPDATED = function(status, charIdx)
    if status ~= "refreshed" then
      SetReadyToSelectCharacter(true)
    end
    if status == "deleted" then
      HideEditDialog(characterSelectWindow)
      char_selIndex = nil
      UpdateList(1)
      SelectedReanchor(1)
      for i = 1, MAX_CHARACTOR do
        if i ~= 1 then
          charButtonList[i]:CloseFolder()
        else
          charButtonList[i]:OpenFolder()
        end
      end
    elseif status == "delete_requested" then
      HideEditDialog(characterSelectWindow)
      local selectedIdx = FindSelectedCharacterIdx()
      if selectedIdx ~= nil then
        UpdateList(selectedIdx)
      end
      UIParent:LogAlways("delete_requested")
    elseif status == "delete_canceled" then
      local selectedIdx = FindSelectedCharacterIdx()
      if selectedIdx ~= nil then
        UpdateList(selectedIdx)
      end
    elseif status == "error_character_delete_failed" or status == "error_char_name_mismatch" or status == "error_cancel_character_delete_failed" or status == "error_already_requested_character_delete" or status == "error_already_requested_character_transfer" or status == "error_character_connection_restrict" or status == "error_character_expedition_owner" or status == "error_character_faction_owner" or status == "cannot_delete_char_while_on_play" or status == "cannot_delete_char_while_penalty" or status == "cannot_delete_char_while_bot_suspected" then
      HideEditDialog(characterSelectWindow)
      
      local function DialogNoticeHandler(wnd)
        local data = locale.messageBox[status]
        wnd:SetTitle(data.title)
        wnd:SetContent(data.body)
      end
      
      X2DialogManager:RequestNoticeDialog(DialogNoticeHandler, eventWnd:GetId())
    elseif status == "refreshed" then
      UpateList_Enable()
    end
  end,
  LP_MANAGE_CHARACTER_CHANGED = function(newCharId, index)
  end,
  SHOW_CHARACTER_SELECT_WINDOW = function(visible)
    characterSelectWindow.rightPanel:Show(visible, 500)
    characterSelectWindow.bottomPanel:Show(visible, 500)
    if visible then
      SetReadyToSelectCharacter(true)
      X2LoginCharacter:RequestCharacterListRefresh(true)
    end
  end,
  SECOND_PASSWORD_CHECK_COMPLETED = function(success)
    if success then
      return
    end
    
    local function DialogHandler(wnd, infoTable)
      wnd:SetTitle(locale.messageBox.secondPasswordConfirmFail.title)
      local curFailCnt, maxFailCnt = X2Security:GetSecondPasswordFailedCount()
      wnd:SetContent(locale.messageBox.secondPasswordConfirmFail.body(FONT_COLOR_HEX.RED, curFailCnt, maxFailCnt))
    end
    
    X2DialogManager:RequestNoticeDialog(DialogHandler, eventWnd:GetId())
  end,
  SECOND_PASSWORD_CHECK_OVER_FAILED = function()
    local function DialogHandler(wnd, infoTable)
      wnd:SetTitle(locale.messageBox.secondPasswordCheckOverFailed.title)
      
      local curFailCnt, maxFailCnt = X2Security:GetSecondPasswordFailedCount()
      wnd:SetContent(locale.secondPassword.account_lock(maxFailCnt))
    end
    
    X2DialogManager:RequestNoticeDialog(DialogHandler, eventWnd:GetId())
  end,
  SECOND_PASSWORD_ACCOUNT_LOCKED = function()
    local function DialogHandler(wnd, infoTable)
      local function GetSecondPasswordUnlockRemainTime()
        local remainDate = X2Security:GetSecondPasswordUnlockRemainTime()
        
        local msg = locale.time.GetRemainDateToDateFormat(remainDate)
        return locale.secondPassword.lock_state_played(msg)
      end
      
      wnd:SetTitle(locale.messageBox.second_password_account_locked.title)
      local msg = GetSecondPasswordUnlockRemainTime()
      wnd:SetContent(msg)
    end
    
    X2DialogManager:RequestNoticeDialog(DialogHandler, eventWnd:GetId())
  end,
  OPEN_WORLD_QUEUE = function()
    UpdateWorldEntranceWindow()
  end,
  REFRESH_WORLD_QUEUE = function()
    UpdateWorldEntranceWindow()
  end,
  WEB_BROWSER_ESC_EVENT = function(browser)
    if browser == staffWindow.browser then
      ShowStaffWidnow(false)
    end
  end
}
eventWnd:SetHandler("OnEvent", function(this, event, ...)
  eventHandler[event](...)
end)
RegistUIEvent(eventWnd, eventHandler)
local changeToCreateFadeEvents = {
  FADE_INOUT_DONE = function(param)
    if param == "CHANGE_TO_CREATE" then
      X2LoginCharacter:CreateCharacter()
    end
    X2DialogManager:DeleteByOwnerWindow(eventWnd:GetId())
  end
}
characterSelectWindow:SetHandler("OnEvent", function(this, event, ...)
  changeToCreateFadeEvents[event](...)
end)
characterSelectWindow:RegisterEvent("FADE_INOUT_DONE")

function characterSelectWindow:OnScale()
  self:AddAnchor("TOPLEFT", "UIParent", "TOPLEFT", 0, 0)
  self:AddAnchor("BOTTOMRIGHT", "UIParent", "BOTTOMRIGHT", 0, 0)
  if chInfoWindow ~= nil then
    chInfoWindow:ReAnchorChildWnd()
  end
end

characterSelectWindow:SetHandler("OnScale", characterSelectWindow.OnScale)
if serverButton then
  function serverButton:OnClick()
    if X2World:LeaveWorld(EXIT_TO_WORLD_LIST) then
      SetReadyToSelectCharacter(false)
    end
  end
  
  serverButton:SetHandler("OnClick", serverButton.OnClick)
end
