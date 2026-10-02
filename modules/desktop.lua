hl.config({
  general = {
    gaps_in = 1,
    gaps_out = { top = 1, left = 2, right = 2, bottom = 2 },
    border_size = 1,
  },
  decoration = {
    rounding = 12,
    rounding_power = 4,
    shadow = { enabled = true, range = 24, render_power = 3,
      offset = { 0, 6 } },
    blur = { enabled = true, size = 8, passes = 2, new_optimizations = true },
  },
  group = { groupbar = { font_family = "Inter", font_size = 13 } },
})
hl.layer_rule({
  match = { namespace = "^omarchy-keyboard-panel$" },
  blur = true, xray = false, ignore_alpha = 0.2,
})
