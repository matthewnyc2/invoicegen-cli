"""Brutalist Command theme tokens for InvoiceGen Rich output."""

from rich.theme import Theme

# ── Design Tokens ──────────────────────────────────────────────
# Stitch: "The Brutalist Command"
# Surface:   #0e0e0e
# Primary:   #9fff88 (green)
# Secondary: #00fbfb (cyan)
# Tertiary:  #44a5ff (blue)
# Fonts:     Space Grotesk (headlines), JetBrains Mono (data)
# Borders:   Ghost borders at 20% opacity only
# Tables:    Unicode box-drawing (no rounded corners)

SURFACE = "#0e0e0e"
PRIMARY = "#9fff88"
PRIMARY_DIM = "#4a8040"
SECONDARY = "#00fbfb"
TERTIARY = "#44a5ff"
ERROR = "#ff5555"
WARNING = "#ffcc00"
MUTED = "#666666"
GHOST = "#333333"

BRUTALIST_THEME = Theme(
    {
        # Core
        "primary": f"bold {PRIMARY}",
        "secondary": f"bold {SECONDARY}",
        "tertiary": f"bold {TERTIARY}",
        "muted": f"{MUTED}",
        "ghost": f"{GHOST}",
        "error": f"bold {ERROR}",
        "warning": f"{WARNING}",
        # Table elements
        "table.header": f"bold {SECONDARY}",
        "table.border": GHOST,
        "table.title": f"bold {SECONDARY}",
        # Data
        "data.money": PRIMARY,
        "data.id": MUTED,
        "data.label": f"bold {SECONDARY}",
        # Status
        "status.paid": f"bold {PRIMARY}",
        "status.sent": f"bold {TERTIARY}",
        "status.draft": MUTED,
        "status.overdue": f"bold {ERROR}",
        # Bar chart
        "bar.fill": PRIMARY,
        "bar.empty": GHOST,
        "bar.fill.cyan": SECONDARY,
        # Panel
        "panel.border": GHOST,
        "panel.title": f"bold {SECONDARY}",
        # Prompt
        "prompt": PRIMARY,
    }
)

# Unicode box-drawing characters for tables
BOX_H = "\u2501"   # ━
BOX_V = "\u2503"   # ┃
BOX_TL = "\u250f"  # ┏
BOX_TR = "\u2513"  # ┓
BOX_BL = "\u2517"  # ┗
BOX_BR = "\u251b"  # ┛

# Block elements for bar charts
BLOCK_FULL = "\u2588"    # █
BLOCK_DARK = "\u2593"    # ▓
BLOCK_MED = "\u2592"     # ▒
BLOCK_LIGHT = "\u2591"   # ░
