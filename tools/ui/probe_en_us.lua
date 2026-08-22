-- probe_en_us.lua — compiles to a chunk that replaces world_select's locale
-- table with a MARKED one: if the screen still shows normal layout/texts, this
-- file is NOT being loaded from the pak; if texts/layout break or markers
-- appear, it IS loaded (and our execution model is right).

local t = {}
t.made_html_path = "ui/login_stage/html/made_en.html"
t.worldSelectLocale = "PROBE_ADDON_WAS_LOADED"
return t
