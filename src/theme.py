from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    app_bg: str
    plot_bg: str
    font: str
    card_bg: str
    card_border: str
    border_subtle: str
    muted_text: str
    template: str
    root_fill: str
    text_on_dark: str
    text_on_light: str


THEMES: dict[str, Theme] = {
    "dark": Theme(
        name="dark",
        app_bg="#0f1115",
        plot_bg="#0f1115",
        font="#ffffff",
        card_bg="#11151b",
        card_border="#2a2f3a",
        border_subtle="#2a2f3a",
        muted_text="#adb5c6",
        template="plotly_dark",
        root_fill="#1c1f26",
        text_on_dark="#f8f9ff",
        text_on_light="#11151b",
    ),
    "light": Theme(
        name="light",
        app_bg="#f8fafc",
        plot_bg="#ffffff",
        font="#0f172a",
        card_bg="#ffffff",
        card_border="#e2e8f0",
        border_subtle="#cbd5e1",
        muted_text="#475569",
        template="plotly_white",
        root_fill="#e2e8f0",
        text_on_dark="#0f172a",
        text_on_light="#0f172a",
    ),
}

DEFAULT_THEME = THEMES["dark"]

# CSS variable helpers (used in layout styles)
CUSTOM_BG = "var(--app-bg)"
PLOT_BG = "var(--plot-bg)"
FONT_COL = "var(--text-color)"

CUSTOM_CARD = {
    "padding": "8px",
    "backgroundColor": "var(--card-bg)",
    "border": "1px solid var(--card-border)",
    "borderRadius": "8px",
}

MODAL_BASE_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "width": "100vw",
    "height": "100vh",
    "backgroundColor": "rgba(0,0,0,0.55)",
    "alignItems": "center",
    "justifyContent": "center",
    "zIndex": 1000,
    "padding": "16px",
}
MODAL_HIDDEN_STYLE = {**MODAL_BASE_STYLE, "display": "none"}
MODAL_VISIBLE_STYLE = {**MODAL_BASE_STYLE, "display": "flex"}
MODAL_CARD_STYLE = {**CUSTOM_CARD, "maxWidth": "380px", "width": "100%", "textAlign": "center"}


def get_theme(name: str | None) -> Theme:
    if not name:
        return DEFAULT_THEME
    return THEMES.get(name, DEFAULT_THEME)
