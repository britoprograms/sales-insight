# Simple theme registry. Default is 'mono' (black background, white text).
THEMES = {
    "mono": {
        "bg":"#000000",
        "fg":"#FFFFFF",
        "accent":"#FFFFFF",
        "muted":"#AAAAAA",
        "table_header":"#FFFFFF",
    },
    "matrix": {
        "bg":"#000000",
        "fg":"#00FF7F",
        "accent":"#00FF7F",
        "muted":"#00995a",
        "table_header":"#00FF7F",
    },
    "light": {
        "bg":"#FFFFFF",
        "fg":"#111111",
        "accent":"#333333",
        "muted":"#777777",
        "table_header":"#111111",
    }
}

ORDER = ["mono","matrix","light"]

def get_theme_colors(theme_name: str = "mono") -> dict:
    """Get theme colors, with fallback to mono if theme doesn't exist."""
    return THEMES.get(theme_name, THEMES["mono"])

def generate_css_for_theme(theme_name: str) -> str:
    """Generate CSS string for a specific theme."""
    colors = get_theme_colors(theme_name)
    return f"""
    Screen.theme-{theme_name} {{ 
        background: {colors['bg']}; 
        color: {colors['fg']}; 
    }}
    Screen.theme-{theme_name} #sidebar {{ 
        border: heavy {colors['accent']}; 
    }}
    Screen.theme-{theme_name} #statusbar {{ 
        color: {colors['muted']}; 
    }}
    Screen.theme-{theme_name} .nav-title {{ 
        color: {colors['accent']}; 
    }}
    """

def generate_all_theme_css() -> str:
    """Generate CSS for all themes."""
    css_parts = []
    for theme_name in ORDER:
        css_parts.append(generate_css_for_theme(theme_name))
    return "\n".join(css_parts)

