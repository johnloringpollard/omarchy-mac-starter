-- Theme-local overrides: Omarchy restores its defaults when switching themes.
hl.config({
  general = {
    gaps_in = 6,
    gaps_out = 12,
    border_size = 1,
    col = {
      active_border = "rgba(007affbb)",
      inactive_border = "rgba(00000024)",
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
      color = "rgba(00000024)",
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
      border_active = "rgba(007affbb)",
      border_inactive = "rgba(00000024)",
    },
    groupbar = {
      font_family = "Inter",
      font_size = 13,
      font_weight_active = "semibold",
      font_weight_inactive = "normal",
      height = 26,
      text_color = "rgb(1d1d1f)",
      text_color_inactive = "rgb(636368)",
      col = { active = "rgb(cde4ff)", inactive = "rgb(ececef)" },
      gradient_rounding = 8,
    },
  },
})

hl.curve("appleEase", { type = "bezier", points = { { 0.2, 0.8 }, { 0.2, 1 } } })
hl.animation({ leaf = "windowsIn", enabled = true, speed = 3, bezier = "appleEase", style = "popin 96%" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 2, bezier = "appleEase", style = "popin 98%" })
hl.animation({ leaf = "layersIn", enabled = true, speed = 2, bezier = "appleEase", style = "fade" })
hl.animation({ leaf = "layersOut", enabled = true, speed = 1.5, bezier = "appleEase", style = "fade" })
