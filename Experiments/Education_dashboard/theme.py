CUSTOM_BG = "#0f1115"
PLOT_BG = "#0f1115"
FONT_COL = "#ffffff"

CUSTOM_CARD = {
    "padding": "8px",
    "backgroundColor": "#11151b",
    "border": "1px solid #2a2f3a",
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
