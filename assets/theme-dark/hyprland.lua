-- Theme-local overrides: Omarchy restores its defaults when switching themes.
hl.config({
  general = {
    gaps_in = 1,
    gaps_out = { top = 1, left = 2, right = 2, bottom = 2 },
    border_size = 1,
    col = {
      active_border = "rgba(78b4ffbb)",
      inactive_border = "rgba(ffffff22)",
    },
  },
  decoration = {
    rounding = 12,
    rounding_power = 4,
    active_opacity = 1.0,
    inactive_opacity = 1.0,
    shadow = {
      enabled = true,
      range = 24,
      render_power = 3,
      color = "rgba(00000066)",
      offset = { 0, 6 },
    },
    blur = {
      enabled = true,
      size = 8,
      passes = 2,
      new_optimizations = true,
    },
  },
  group = {
    col = {
      border_active = "rgba(78b4ffbb)",
      border_inactive = "rgba(ffffff22)",
    },
    groupbar = {
      font_family = "Inter",
      font_size = 13,
      font_weight_active = "semibold",
      font_weight_inactive = "normal",
      height = 26,
      text_color = "rgb(f2f3f5)",
      text_color_inactive = "rgb(b6b8c1)",
      col = { active = "rgb(25486e)", inactive = "rgb(252830)" },
      gradient_rounding = 8,
    },
  },
})

hl.curve("appleEase", { type = "bezier", points = { { 0.2, 0.8 }, { 0.2, 1 } } })
hl.animation({ leaf = "windowsIn", enabled = true, speed = 3, bezier = "appleEase", style = "popin 96%" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 2, bezier = "appleEase", style = "popin 98%" })
hl.animation({ leaf = "layersIn", enabled = true, speed = 2, bezier = "appleEase", style = "fade" })
hl.animation({ leaf = "layersOut", enabled = true, speed = 1.5, bezier = "appleEase", style = "fade" })
