if characterSelectLocale == nil then
  characterSelectLocale = {}
end

function characterSelectLocale.AdjustLocaleButtonFont(buttonStyles, deleteStyles, createStyle)
end

function characterSelectLocale.GetLaborPowerText(curLabor, maxLabor)
  return string.format("\194\183 %s |,%d;/|,%d;", locale.attribute("labor_power"), curLabor, maxLabor)
end

characterSelectLocale.serverTransferIcon = {
  coords = {
    184,
    321,
    98,
    23
  },
  anchor = {100, 3}
}
characterSelectLocale.showReturnServer = true

function characterSelectLocale.CreateStaffButton(bottomPanel)
  return nil
end
