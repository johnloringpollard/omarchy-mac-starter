local function application_key(mods, key, ghostty_mods)
  return function()
    local window = hl.get_active_window()
    if not window then return end
    local target_mods = mods
    if window.class == "com.mitchellh.ghostty" then
      if not ghostty_mods then return end
      target_mods = ghostty_mods
    else
      for _, tag in ipairs(window.tags or {}) do
        if tag:gsub("%*$", "") == "terminal" then return end
      end
    end
    hl.dispatch(hl.dsp.send_key_state({ mods = target_mods, key = key, state = "down" }))
    hl.timer(function()
      hl.dispatch(hl.dsp.send_key_state({ mods = target_mods, key = key, state = "up" }))
    end, { timeout = 50, type = "oneshot" })
  end
end

local shortcuts = {
  { "SUPER + A", "Select all", "CTRL", "A", "CTRL SHIFT" },
  { "SUPER + Z", "Undo", "CTRL", "Z" },
  { "SUPER + SHIFT + Z", "Redo", "CTRL SHIFT", "Z" },
  { "SUPER + SHIFT + T", "Reopen closed tab", "CTRL SHIFT", "T" },
  { "SUPER + R", "Reload page", "CTRL", "R" },
  { "SUPER + T", "New tab", "CTRL", "T", "CTRL SHIFT" },
}
for _, binding in ipairs(shortcuts) do
  hl.unbind(binding[1])
  o.bind(binding[1], binding[2], application_key(binding[3], binding[4], binding[5]))
end
hl.unbind("SUPER + ALT + T")
o.bind("SUPER + ALT + T", "Toggle floating", hl.dsp.window.float({ action = "toggle" }))
hl.config({
  input = { touchpad = { natural_scroll = true } },
  gestures = {
    workspace_swipe_invert = true, workspace_swipe_create_new = false,
    workspace_swipe_forever = false, workspace_swipe_use_r = false,
  },
})
-- Hyprland rejects a second 3-finger horizontal gesture, so skip ours when
-- the user's input.lua already enables one.
local function has_workspace_gesture()
  local file = io.open((os.getenv("HOME") or "") .. "/.config/hypr/input.lua")
  if not file then return false end
  for line in file:lines() do
    if not line:match("^%s*%-%-") and line:match("hl%.gesture") and line:match("fingers%s*=%s*3")
      and line:match('direction%s*=%s*"horizontal"') then
      file:close()
      return true
    end
  end
  file:close()
  return false
end
if not has_workspace_gesture() then
  hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
end
