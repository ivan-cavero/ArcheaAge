RACE_TYPE = {
  RACE_NUIAN,
  RACE_ELF,
  RACE_FERRE,
  RACE_HARIHARAN
}
local featureSet = X2Player:GetFeatureSet()
if featureSet ~= nil and featureSet.dwarfWarborn then
  RACE_TYPE = {
    RACE_NUIAN,
    RACE_ELF,
    RACE_DWARF,
    RACE_FERRE,
    RACE_HARIHARAN,
    RACE_WARBORN
  }
end
GENDER_TYPE = {GENDER_MALE, GENDER_FEMALE}
RACE_COLOR_TABEL = {}
RACE_COLOR_TABEL[RACE_NUIAN] = {
  ConvertColor(177),
  ConvertColor(191),
  ConvertColor(160),
  1
}
RACE_COLOR_TABEL[RACE_ELF] = {
  ConvertColor(168),
  ConvertColor(161),
  ConvertColor(182),
  1
}
RACE_COLOR_TABEL[RACE_FERRE] = {
  ConvertColor(144),
  ConvertColor(175),
  ConvertColor(194),
  1
}
RACE_COLOR_TABEL[RACE_HARIHARAN] = {
  ConvertColor(209),
  ConvertColor(202),
  ConvertColor(147),
  1
}
RACE_COLOR_TABEL[RACE_DWARF] = {
  ConvertColor(177),
  ConvertColor(191),
  ConvertColor(160),
  1
}
RACE_COLOR_TABEL[RACE_WARBORN] = {
  ConvertColor(177),
  ConvertColor(191),
  ConvertColor(160),
  1
}
STEP1_BG_PATH = {}
STEP1_BG_PATH[RACE_NUIAN] = "ui/login_stage/background/step1_nuian.dds"
STEP1_BG_PATH[RACE_ELF] = "ui/login_stage/background/step1_elf.dds"
STEP1_BG_PATH[RACE_FERRE] = "ui/login_stage/background/step1_ferre.dds"
STEP1_BG_PATH[RACE_HARIHARAN] = "ui/login_stage/background/step1_hariharan.dds"
STEP1_BG_PATH[RACE_DWARF] = "ui/login_stage/background/step1_nuian.dds"
STEP1_BG_PATH[RACE_WARBORN] = "ui/login_stage/background/step1_nuian.dds"
STEP2_BG_PATH = {}
STEP2_BG_PATH[RACE_NUIAN] = "ui/login_stage/background/step1_nuian.dds"
STEP2_BG_PATH[RACE_ELF] = "ui/login_stage/background/step1_elf.dds"
STEP2_BG_PATH[RACE_FERRE] = "ui/login_stage/background/step1_ferre.dds"
STEP2_BG_PATH[RACE_HARIHARAN] = "ui/login_stage/background/step1_hariharan.dds"
STEP2_BG_PATH[RACE_DWARF] = "ui/login_stage/background/step1_nuian.dds"
STEP2_BG_PATH[RACE_WARBORN] = "ui/login_stage/background/step1_nuian.dds"
STEP3_BG_PATH = {}
STEP3_BG_PATH[RACE_NUIAN] = "ui/login_stage/background/step3_nuian.dds"
STEP3_BG_PATH[RACE_ELF] = "ui/login_stage/background/step3_elf.dds"
STEP3_BG_PATH[RACE_FERRE] = "ui/login_stage/background/step3_ferre.dds"
STEP3_BG_PATH[RACE_HARIHARAN] = "ui/login_stage/background/step3_hariharan.dds"
STEP3_BG_PATH[RACE_DWARF] = "ui/login_stage/background/step3_nuian.dds"
STEP3_BG_PATH[RACE_WARBORN] = "ui/login_stage/background/step3_nuian.dds"

function GetRaceNameIndex(raceName)
  for i = 1, #RACE_TYPE do
    if raceName == X2Unit:GetRaceStr(RACE_TYPE[i]) then
      return RACE_TYPE[i]
    end
  end
  return nil
end

function GetGenderIndex(gender)
  for i = 1, #GENDER_TYPE do
    if gender == X2Unit:GetGenderStr(GENDER_TYPE[i]) then
      return GENDER_TYPE[i]
    end
  end
  return nil
end

FACE = 1
EYES = 2
NOSE = 3
MOUTH = 4
SHAPE = 5
MAX_PRESET_TYPE = SHAPE
HAIR_TAB = 1
EYE_TAB = HAIR_TAB + 1
MAKEUP_TAB = EYE_TAB + 1
SKIN_TAB = MAKEUP_TAB + 1
TATTOO_TAB = SKIN_TAB + 1
MAX_TAB_TYPE = TATTOO_TAB
HAIR_TYPE = 1
HAIR_COLOR = HAIR_TYPE + 1
EYEBROW_TYPE = HAIR_COLOR + 1
EYEBROW_COLOR = EYEBROW_TYPE + 1
PUPIL_COLOR = EYEBROW_COLOR + 1
EYE_MAKEUP = PUPIL_COLOR + 1
LIPS_COLOR = EYE_MAKEUP + 1
CHEEK_TYPE = LIPS_COLOR + 1
MUSTACHE_TYPE = CHEEK_TYPE + 1
MUSTACHE_COLOR = MUSTACHE_TYPE + 1
SKIN_TYPE = MUSTACHE_COLOR + 1
SKIN_COLOR = SKIN_TYPE + 1
WRINKLE_TYPE = SKIN_COLOR + 1
TATTOO_TYPE = WRINKLE_TYPE + 1
SCAR_TYPE = TATTOO_TYPE + 1
MAX_STYLE_TYPE = SCAR_TYPE
EMPTY_STYLE = MAX_STYLE_TYPE + 1
STYLE_PALLET = 1
STYLE_COMPOUND = 2
STYLE_PAGE_DEFAULT_COUNT = 3
STYLE_PAGE_NOT_DEFAULT_COUNT = 4
STYLE_PAGE_USE_SLIDER_DEFAULT_COUNT = 5
STYLE_PAGE_USE_SLIDER_NOT_DEFAULT_COUNT = 6
STYLE_WINDOW_TYPE = {
  STYLE_PAGE_DEFAULT_COUNT,
  STYLE_PAGE_DEFAULT_COUNT,
  STYLE_PAGE_DEFAULT_COUNT,
  STYLE_PALLET,
  STYLE_PALLET,
  STYLE_PAGE_USE_SLIDER_NOT_DEFAULT_COUNT,
  STYLE_PALLET,
  STYLE_PAGE_USE_SLIDER_NOT_DEFAULT_COUNT,
  STYLE_PAGE_USE_SLIDER_NOT_DEFAULT_COUNT,
  STYLE_PALLET,
  STYLE_PAGE_DEFAULT_COUNT,
  STYLE_PAGE_DEFAULT_COUNT,
  STYLE_PAGE_USE_SLIDER_DEFAULT_COUNT,
  STYLE_PAGE_NOT_DEFAULT_COUNT,
  STYLE_COMPOUND
}
STYLE_MAX_ITEM = {
  2,
  2,
  2,
  0,
  0,
  2,
  0,
  2,
  2,
  0,
  2,
  2,
  2,
  2,
  2
}
STYLE_DELETE = {
  false,
  false,
  true,
  false,
  false,
  true,
  false,
  true,
  true,
  false,
  false,
  false,
  true,
  true,
  true
}
CUSTOMIZE_INSET = 15
CUSTOMIZE_ITEM_WIDTH = 126
CUSTOMIZE_ITEM_BIG = 126
CUSTOMIZE_ITEM_NORMAL = 100
CUSTOMIZE_ITEM_SMALL = 85
CUSTOMIZE_ITEM_PAGE = 84
PRESET_ITEM_WIDTH = 125
PRESET_ITEM_HEIGHT = 120
CUSTOMIZE_ITEM_HEIGHT = {
  CUSTOMIZE_ITEM_BIG,
  CUSTOMIZE_ITEM_NORMAL,
  CUSTOMIZE_ITEM_SMALL,
  CUSTOMIZE_ITEM_PAGE
}
