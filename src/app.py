from __future__ import annotations
from pathlib import Path
import numpy as np
from dash import (
    Dash,
    ALL,
    Input,
    Output,
    State,
    callback_context,
    dcc,
    html,
)
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from data_loader import load_data
from plots import (
    PARCOORD_DEFAULT_VARS,
    PARCOORD_LABELS,
    PARCOORD_VARIABLES,
    TREEMAP_DRILL_METRICS,
    build_city_treemap,
    build_color_map_for_selected,
    build_detail_table,
    build_parcoord_legend,
    build_parcoord_sliders,
    build_parallel_coordinates,
    build_selection_bubble,
    build_treemap_drill_chart,
    build_leaflet_map,
)
from theme import CUSTOM_BG, CUSTOM_CARD, FONT_COL, get_theme

data = load_data()

ASSETS_PATH = Path(__file__).resolve().parents[0] / "assets"

app = Dash(__name__, assets_folder=str(ASSETS_PATH), title="Education Dashboard")

TREEMAP_PROMPT = "Click an education cell in the treemap to add it for comparison."


def render_selection_rows(values):
    rows = []
    visible_index = 1
    for idx, value in enumerate(values, start=1):
        has_value = bool(value)
        label = f"{visible_index}. {value}" if has_value else ""
        if has_value:
            visible_index += 1
        rows.append(
            html.Div(
                [
                    html.Span(label, style={"flex": "1"}),
                    html.Button(
                        "🗑",
                        id=f"remove_edu{idx}",
                        n_clicks=0,
                        style={
                            "backgroundColor": "#b02a37",
                            "color": "#fff",
                            "border": "none",
                            "padding": "3px 9px",
                            "borderRadius": "6px",
                            "cursor": "pointer",
                            "fontSize": "18px",
                        },
                    ),
                ],

                style={
                    "display": "flex" if has_value else "none",
                    "alignItems": "center",
                    "gap": "8px",
                    "marginBottom": "6px",
                },
            )
        )

    if visible_index == 1:
        rows.insert(
            0,
            html.Div(
                "No educations selected yet.",
                style={"color": "var(--muted-text)", "marginBottom": "6px"},
            ),
        )
    return rows

titles_options = [{"label": t, "value": t} for t in data.available_titles]
parcoord_available = [c for c in PARCOORD_VARIABLES if c in data.df.columns]
parcoord_default = [c for c in PARCOORD_DEFAULT_VARS if c in parcoord_available] or parcoord_available[:5]
parcoord_options = [{"label": PARCOORD_LABELS.get(c, c), "value": c} for c in parcoord_available]
dropdown_style = {
    "marginBottom": "10px",
    "backgroundColor": "var(--control-bg)",
    "color": FONT_COL,
    "border": "1px solid var(--control-border)",
    'width': '250px',
}
MAX_SELECTIONS = 6
selection_inputs = [Input(f"edu{i}", "value") for i in range(1, MAX_SELECTIONS + 1)]
selection_states = [State(f"edu{i}", "value") for i in range(1, MAX_SELECTIONS + 1)]
selection_outputs = [Output(f"edu{i}", "value") for i in range(1, MAX_SELECTIONS + 1)]
remove_inputs = [Input(f"remove_edu{i}", "n_clicks") for i in range(1, MAX_SELECTIONS + 1)]
selection_error_output = Output("selection_error", "children")
selection_limit_dialog_outputs = [
    Output("selection_limit_dialog", "displayed"),
    Output("selection_limit_dialog", "message"),
]


app.layout = html.Div(
    style={"padding": "12px", "backgroundColor": CUSTOM_BG, "color": FONT_COL, "minHeight": "100vh", "fontFamily": "var(--font-family, Arial, sans-serif)"},
    children=[
        dcc.Store(id="theme_store", data="light", storage_type="local"),

        html.Div(
            [
                html.H1("EduEx - Educational explorer dashboard", style={"marginBottom": "12px", "width": "100%"}),

                html.Div(
                    [
                        html.Div("Lol", id="theme_status", style={"fontSize": "14px", "color": "var(--muted-text)"}),
                        html.Button(
                            "Skift til lys tilstand",
                            id="theme_toggle",
                            n_clicks=0,
                            style={
                                "padding": "6px 12px",
                                "backgroundColor": "#3b82f6",
                                "color": "#fff",
                                "border": "none",
                                "borderRadius": "6px",
                                "cursor": "pointer",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "gap": "12px",
                        "marginBottom": "12px",
                    },
                ),
            ], style={'display': 'flex', 'gap': '12px'},
        ),

        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        dcc.Graph(id="treemap", style={"height": "620px", "width": "100%"}),
                                        html.Div(
                                            id="treemap_overlay",
                                            style={
                                                "position": "absolute",
                                                "display": "none",
                                                "pointerEvents": "auto",
                                                "zIndex": 5,
                                                "top": 0,
                                                "left": 0,
                                            },
                                        ),
                                    ], style={"position": "relative", "width": "100%"},
                                ),
                                html.Div(
                                    [
                                        html.Div("Treemap of educations in Denmark. Click a cell to see details for the education, and add it for comparison.", style={"marginBottom": "6px", "marginTop": "10px", "fontStyle": "italic"}),
                                        html.Div(
                                            [
                                                html.Div("Filter by cities:", style={"marginBottom": "6px", "fontWeight": "600"}),
                                                dcc.Dropdown(
                                                    data.city_options,
                                                    id="city_select",
                                                    value="__ALL__",
                                                    clearable=False,
                                                    style=dropdown_style,
                                                    className="dark-dropdown",
                                                ),
                                            ]
                                        ),
                                        html.Div(
                                            [
                                                html.Div("Select size for areas:", style={"marginBottom": "6px", "fontWeight": "600"}),
                                                dcc.Dropdown(
                                                    data.size_options,
                                                    id="size_metric",
                                                    value="optagne",
                                                    clearable=False,
                                                    style=dropdown_style,
                                                    className="dark-dropdown",
                                                ),
                                            ]
                                        ),

                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.Div(
                                                            TREEMAP_PROMPT,
                                                            id="treemap_pending_label",
                                                            style={"flex": "1"},
                                                        ),
                                                        html.Button(
                                                            "Add to comparison",
                                                            id="treemap_add",
                                                            disabled=True,
                                                            style={
                                                                "padding": "6px 14px",
                                                                "backgroundColor": "#2b8a3e",
                                                                "color": "#fff",
                                                                "border": "none",
                                                                "borderRadius": "4px",
                                                                "cursor": "pointer",
                                                            },
                                                        ),
                                                    ],
                                                    style={
                                                        "display": "flex",
                                                        "gap": "10px",
                                                        "alignItems": "center",
                                                        "flexWrap": "wrap",
                                                        "marginBottom": "10px",
                                                    },
                                                ),

                                                html.Div("Chosen educations:", style={"fontWeight": "600", "marginBottom": "6px"}),
                                                html.Div(
                                                    render_selection_rows([None]*MAX_SELECTIONS),
                                                    id="selection_summary_text",
                                                    style={"marginBottom": "10px", "lineHeight": "1.5"},
                                                ),
                                                html.Div(
                                                    "",
                                                    id="selection_error",
                                                    style={"color": "#b02a37", "marginBottom": "6px", "fontWeight": "600"},
                                                ),
                                                html.Button(
                                                    "Clear selections",
                                                    id="clear_selections",
                                                    style={
                                                        "alignSelf": "flex-start",
                                                        "padding": "6px 14px",
                                                        "backgroundColor": "#444d5c",
                                                        "color": "#fff",
                                                        "border": "none",
                                                        "borderRadius": "4px",
                                                    },
                                                ),
                                                dcc.ConfirmDialog(
                                                    id="selection_limit_dialog",
                                                    displayed=False,
                                                    message="",
                                                ),
                                            ],
                                            style={**CUSTOM_CARD, "marginTop": "10px"},
                                        ),
                                    ], style={'width': '15%'},
                                ),
                            ], style={'display': 'flex', 'gap': '12px'},
                        ),
                    ],
                    style={"flex": "1 1 1100px", "minWidth": "640px"},
                ),
            ],
            style={"display": "flex", "gap": "16px", "alignItems": "flex-start", "flexWrap": "wrap"},
        ),

        html.Div(
            [
                dcc.Dropdown(titles_options, id=f"edu{i}", clearable=True)
                for i in range(1, MAX_SELECTIONS + 1)
            ],
            style={"display": "none"},
        ),

        html.Hr(style={"borderColor": "var(--divider)"}),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Select variables of your interest:", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.Dropdown(
                            parcoord_options,
                            id="parcoord_vars",
                            value=parcoord_default,
                            multi=True,
                            placeholder="Choose variables to display",
                            style={
                                "marginBottom": "12px",
                                "backgroundColor": "var(--control-bg)",
                                "color": FONT_COL,
                                "border": "1px solid var(--control-border)",
                            },
                            className="dark-dropdown",
                        ),
                        html.Div(id="parcoord_legend", style={"marginBottom": "12px"}),
                        html.Iframe(
                            id="parallel_plot",
                            style={
                                "width": "100%",
                                "height": "640px",  #Change Parallel coordinates plot size here 
                                "border": "0",
                                "backgroundColor": CUSTOM_BG,
                            },
                        ),
                    ],
                    style={"flex": "4 1 0px", "minWidth": "620px", **CUSTOM_CARD},
                ),
                html.Div(
                    [
                        html.H3("Parallel Coordinates Plot", style={"fontWeight": "600", "marginBottom": "6px"}),
                        html.Div("""The plot shows the variables across all
educations in that specific city, or educations on national level. The sliders
select the educations that match the criteria, and are shown in the
bubble chart below. Hover over the name of the slider name to view details for the
likert variables.""", style={"marginBottom": "6px", "marginTop": "10px", "fontStyle": "italic"}),
                        html.Div(
                            [
                                html.Label("Axis scale:", style={"fontWeight": "600"}),
                                dcc.RadioItems(
                                    id="parcoord_scale_mode",
                                    options=[
                                        {"label": "Fixed (2-5)", "value": "FIXED_SCALE"},
                                        {"label": "Global min/max", "value": "DATA_SCALE"},
                                    ],
                                    value="FIXED_SCALE",
                                    labelStyle={"marginRight": "12px"},
                                    style={"marginBottom": "8px"},
                                ),
                            ],
                            style={"marginBottom": "12px"},
                        ),
                        html.Div("Filter educations by variable (hover for details):", style={"fontWeight": "600", "marginBottom": "6px"}),
                        html.Div(id="parcoord_sliders", style={"maxHeight": "640px", "overflowY": "auto"}),
                    ],
                    style={"flex": "1 1 220px", "minWidth": "220px", **CUSTOM_CARD},
                ),
            ],
            style={"display": "flex", "gap": "16px", "alignItems": "stretch", "flexWrap": "wrap"},
        ),

        html.Hr(style={"borderColor": "var(--divider)"}),
        html.Div(
            [
                html.Div(
                    [
                        html.H3("Unemployment, grades and salary", style={"fontWeight": "600", "marginBottom": "6px"}),
                        html.Div("""The bubble chart highlights the selected
educations from the treemap, to compare their unemployment rate and average
grades (kvote 1). The size of the bubbles represents the salary of newly graduated
students.""", style={"marginBottom": "6px", "marginTop": "10px", "fontStyle": "italic"}),
                        html.Div(id="bubble_legend", style={"marginBottom": "12px"}),
                        dcc.Graph(id="selection_bubble", style={"height": "460px"}, config=dict(displayModeBar=False)),
                        dcc.ConfirmDialog(id="bubble_confirm"),
                    ], style={"flex": "1 1 480px", "minWidth": "420px", **CUSTOM_CARD}
                ), 
                html.Div(
                    [
                        html.Div("See details for specific education", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.Dropdown(
                            id="detail_select",
                            options=[],
                            placeholder="Choose an education from your selected list",
                            clearable=True,
                            style=dropdown_style,
                            className="dark-dropdown",
                        ),
                        html.Div(id="detail_table", style={"overflowY": "auto"}),
                    ], style={"flex": "1 1 360px", "minWidth": "320px", **CUSTOM_CARD},
                ),
            ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}
        ), 
        

        dcc.Store(id="treemap_pending"),
        dcc.Store(id="parcoord_color_store", data={}),
        dcc.Store(id="parcoord_filters_store", data={}),
        dcc.Store(id="bubble_pending"),
    ],
)


@app.callback(Output("theme_store", "data"), Input("theme_toggle", "n_clicks"), State("theme_store", "data"), prevent_initial_call=True)
def toggle_theme(n_clicks, current_theme):
    if not n_clicks:
        raise PreventUpdate
    current = current_theme or "dark"
    return "light" if current == "dark" else "dark"

app.clientside_callback(
    """
    function(theme) {
        const mode = theme || 'dark';
        const root = document.documentElement;
        if (root) {
            root.setAttribute('data-theme', mode);
        }
        const buttonLabel = mode === 'light' ? 'Dark mode' : 'Light mode';
        const statusLabel = mode === 'light' ? '' : '';
        return [buttonLabel, statusLabel];
    }
    """,
    Output("theme_toggle", "children"),
    Output("theme_status", "children"),
    Input("theme_store", "data"),
)


@app.callback(
    Output("treemap", "figure"),
    [
        Input("city_select", "value"),
        Input("size_metric", "value"),
        *selection_inputs,
        Input("parcoord_filters_store", "data"),
        Input("theme_store", "data"),
    ],
)
def update_treemap(city_value, metric_key, *args):
    slider_filter = args[-2] if len(args) >= 2 else {}
    theme_name = args[-1] if len(args) >= 1 else None
    selections = list(args[:-2]) if len(args) > 2 else []
    theme = get_theme(theme_name)
    selected = [t for t in selections if t]
    slider_filter = slider_filter or {}
    return build_city_treemap(data, city_value, metric_key, selected, slider_filter, theme)


@app.callback(
    Output("treemap_pending", "data"),
    Output("treemap_pending_label", "children"),
    Output("treemap_add", "disabled"),
    Input("treemap", "clickData"),
    *selection_inputs,
    State("treemap_pending", "data"),
)

def capture_treemap_selection(click_data, *args):
    current_pending = args[-1] if args else None
    selection_values = list(args[:-1]) if args else []
    current_selections = {v for v in selection_values if v}
    ctx = callback_context
    at_limit = len(current_selections) >= MAX_SELECTIONS

    # If the change came from selection updates (e.g., removing an education), clear pending if it no longer exists.
    if ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] != "treemap":
        if current_pending and current_pending not in current_selections:
            return None, TREEMAP_PROMPT, True
        if current_pending and current_pending in current_selections:
            return current_pending, TREEMAP_PROMPT, True
        return current_pending, TREEMAP_PROMPT, not bool(current_pending)

    if not click_data or not click_data.get("points"):
        return None, TREEMAP_PROMPT, True
    label = click_data["points"][0].get("label")
    if not label or label not in data.available_set:
        return None, TREEMAP_PROMPT, True
    if label in current_selections:
        return label, TREEMAP_PROMPT, True
    msg = f"Chosen education: {label}. Click 'Add to comparison' to highlight it."
    # Leave the add button enabled even at limit; the selection callback will show the popup.
    return label, msg, False

@app.callback(
    Output("bubble_pending", "data"),
    Output("bubble_confirm", "displayed"),
    Output("bubble_confirm", "message"),
    Input("selection_bubble", "clickData"),
    selection_inputs,
)
def prompt_add_from_bubble(click_data, *values):
    ctx = callback_context
    # If the callback was triggered by selection changes (remove/clear), do nothing and clear pending.
    if ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] != "selection_bubble":
        return None, False, ""

    current = [v for v in values if v]
    if not click_data or not click_data.get("points"):
        return None, False, ""
    point = click_data["points"][0]
    title = point.get("customdata") or point.get("text")
    if not title or title in current or title not in data.available_set:
        return None, False, ""
    return title, True, f"Vil du tilføje '{title}' til sammenligning?"


@app.callback(
    Output("treemap_overlay", "children"),
    Output("treemap_overlay", "style"),
    Input("treemap", "clickData"),
    Input("city_select", "value"),
    Input("theme_store", "data"),
    Input("treemap_add", "n_clicks"),
)
def show_treemap_drill(click_data, city_value, theme_name, add_clicks):

    base_style = {
        "position": "absolute",
        "display": "none",
        "pointerEvents": "auto",
        "zIndex": 5,
        "top": 0,
        "left": 0,
        "backgroundColor": "var(--card-bg, rgba(0,0,0,0.75))",
        "padding": "6px",
        "borderRadius": "8px",
        "boxShadow": "0 8px 20px rgba(0,0,0,0.35)",
    }

    # Hide the drill overlay once the education has been added to the comparison list.
    if callback_context.triggered and callback_context.triggered[0]["prop_id"].startswith("treemap_add"):
        return None, base_style

    # Hide overlay when city filter changes.
    if callback_context.triggered and callback_context.triggered[0]["prop_id"].split(".")[0] == "city_select":
        return None, base_style

    if not click_data or not click_data.get("points"):
        return None, base_style

    label = click_data["points"][0].get("label")

    if not label or label not in data.available_set:
        return None, base_style

    theme = get_theme(theme_name)

    figs = []
    for metric_key, metric_label in TREEMAP_DRILL_METRICS:
        fig = build_treemap_drill_chart(data, label, metric_key, city_value, theme)
        figs.append(
            html.Div(
                dcc.Graph(figure=fig, style={"height": "240px", "width": "100%"}),
                style={"flex": "1 1 30%", "minWidth": "280px", "maxWidth": "360px"},
            )
        )

    style = dict(base_style)
    style.update(
        {
            "display": "block",
            "width": "75vw",
            "maxWidth": "1200px",
            "minWidth": "680px",
            "maxHeight": "80vh",
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",
        }
    )

    content = html.Div(
        figs,
        style={
            "display": "flex",
            "flexWrap": "wrap",
            "gap": "12px",
            "alignItems": "flex-start",
            "justifyContent": "flex-start",
            "padding": "10px",
        },
    )

    return content, style


@app.callback(
    selection_outputs + [selection_error_output, *selection_limit_dialog_outputs],
    [
        Input("treemap_add", "n_clicks"),
        Input("clear_selections", "n_clicks"),
        *remove_inputs,
        Input("bubble_confirm", "submit_n_clicks"),
        Input("bubble_confirm", "cancel_n_clicks"),
    ],
    [State("treemap_pending", "data"), *selection_states, State("bubble_pending", "data")],
    prevent_initial_call=True,
)
def modify_selections(add_clicks, clear_clicks, *args):
    remove_clicks = list(args[:MAX_SELECTIONS])
    bubble_submit = args[MAX_SELECTIONS]
    bubble_cancel = args[MAX_SELECTIONS + 1]
    pending = args[MAX_SELECTIONS + 2]
    current = list(args[MAX_SELECTIONS + 3: MAX_SELECTIONS + 3 + MAX_SELECTIONS])
    bubble_pending = args[-1] if len(args) > MAX_SELECTIONS * 2 + 3 else None
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    error_text = ""
    show_dialog = False
    dialog_msg = ""

    if trigger == "clear_selections":
        return [None] * MAX_SELECTIONS + [error_text, show_dialog, dialog_msg]

    if trigger.startswith("remove_edu"):
        idx = int(trigger.replace("remove_edu", "")) - 1
        compact = [v for i, v in enumerate(current) if i != idx and v]
        compact += [None] * (MAX_SELECTIONS - len(compact))
        return compact + [error_text, show_dialog, dialog_msg]

    if trigger == "treemap_add":
        if not add_clicks or not pending or pending not in data.available_set:
            raise PreventUpdate
        if pending in current:
            return current + [error_text, show_dialog, dialog_msg]
        for i, val in enumerate(current):
            if not val:
                current[i] = pending
                return current + [error_text, show_dialog, dialog_msg]
        dialog_msg = "Max limit for education comparison hit. Please remove one before adding more."
        show_dialog = True
        return current + [error_text, show_dialog, dialog_msg]

    if trigger == "bubble_confirm":
        if not bubble_submit or not bubble_pending or bubble_pending not in data.available_set:
            raise PreventUpdate
        if bubble_pending in current:
            return current + [error_text, show_dialog, dialog_msg]
        for i, val in enumerate(current):
            if not val:
                current[i] = bubble_pending
                return current + [error_text, show_dialog, dialog_msg]
        dialog_msg = "Max limit for education comparison hit. Please remove one before adding more."
        show_dialog = True
        return current + [error_text, show_dialog, dialog_msg]

    raise PreventUpdate




@app.callback(Output("selection_summary_text", "children"), selection_inputs)
def update_selection_summary(*values):
    return render_selection_rows(list(values))




@app.callback(
    Output("parallel_plot", "srcDoc"),
    Output("parcoord_sliders", "children"),
    Output("parcoord_color_store", "data"),
    Output("parcoord_filters_store", "data"),
    Output("parcoord_legend", "children"),
    Output("bubble_legend", "children"),
    [
        Input("parcoord_vars", "value"),
        *selection_inputs,
        Input("city_select", "value"),
        Input("parcoord_scale_mode", "value"),
        Input({"type": "parcoord-slider", "column": ALL}, "value"),
        Input("theme_store", "data"),
    ],
    [
        State({"type": "parcoord-slider", "column": ALL}, "id"),
        State("parcoord_color_store", "data"),
    ],
)
def update_parallel_plot(*args):
    selected_vars = args[0] if args else None
    selections = list(args[1 : 1 + MAX_SELECTIONS])
    city_value = args[1 + MAX_SELECTIONS] if len(args) > 1 + MAX_SELECTIONS else None
    scale_mode = args[2 + MAX_SELECTIONS] if len(args) > 2 + MAX_SELECTIONS else "FIXED_SCALE"
    slider_values = args[3 + MAX_SELECTIONS] if len(args) > 3 + MAX_SELECTIONS else None
    theme_name = args[4 + MAX_SELECTIONS] if len(args) > 4 + MAX_SELECTIONS else None
    slider_ids = args[5 + MAX_SELECTIONS] if len(args) > 5 + MAX_SELECTIONS else None
    color_store = args[6 + MAX_SELECTIONS] if len(args) > 6 + MAX_SELECTIONS else None

    theme = get_theme(theme_name)
    allowed_titles = None
    if city_value and city_value != "__ALL__":
        allowed_titles = set(
            data.df_prov.loc[data.df_prov["instkommunetx"] == city_value, "titel"]
            .dropna()
            .astype(str)
            .str.strip()
        )
        allowed_titles &= data.available_set

    available = parcoord_available
    chosen = [v for v in (selected_vars or parcoord_default) if v in available]
    if not chosen:
        chosen = available[:5]

    triggered = {t["prop_id"] for t in callback_context.triggered} if callback_context.triggered else set()
    reset_sliders = "city_select.value" in triggered

    prev_slider_values = {}
    if not reset_sliders and slider_ids and slider_values:
        prev_slider_values = {sid["column"]: val for sid, val in zip(slider_ids, slider_values)}

    slider_components, slider_filter = build_parcoord_sliders(data, chosen, prev_slider_values, allowed_titles)
    selected_titles = [t for t in selections if t]
    color_map = build_color_map_for_selected(selected_titles, color_store)
    figure_html = build_parallel_coordinates(
        data,
        selected_titles,
        slider_filter,
        chosen,
        color_map,
        theme,
        allowed_titles,
        scale_mode,
    )
    legend = build_parcoord_legend(selected_titles, color_map, theme)
    return figure_html, slider_components, color_map, slider_filter, legend, legend


# Keep `detail_select` options in sync with the chosen educations (edu1..edu6).
@app.callback(
    Output("detail_select", "options"),
    Output("detail_select", "placeholder"),
    selection_inputs,
)
def update_detail_select_options(*values):
    # Only allow selecting among the currently chosen educations
    chosen = [v for v in values if v]
    if not chosen:
        return [], "Vælg en uddannelse fra dine valgte"
    opts = [{"label": t, "value": t} for t in chosen]
    return opts, "Vælg uddannelse"




@app.callback(
    Output("selection_bubble", "figure"),
    [
        *selection_inputs,
        Input("city_select", "value"),
        Input("parcoord_color_store", "data"),
        Input("parcoord_filters_store", "data"),
        Input("theme_store", "data"),
    ],
)
def update_selection_bubble(*args):
    selections = list(args[:MAX_SELECTIONS])
    city_value = args[MAX_SELECTIONS] if len(args) > MAX_SELECTIONS else None
    color_store = args[MAX_SELECTIONS + 1] if len(args) > MAX_SELECTIONS + 1 else None
    slider_filter = args[MAX_SELECTIONS + 2] if len(args) > MAX_SELECTIONS + 2 else None
    theme_name = args[MAX_SELECTIONS + 3] if len(args) > MAX_SELECTIONS + 3 else None
    theme = get_theme(theme_name)
    titles = [t for t in selections if t]
    color_map = build_color_map_for_selected(titles, color_store)
    return build_selection_bubble(data, titles, color_map, theme, city_value, slider_filter)



@app.callback(
    Output("detail_table", "children"),
    Input("detail_select", "value"),
    Input("theme_store", "data"),
)
def update_detail_panel(edu_title: str | None, theme_name: str):
    theme = get_theme(theme_name)

    if not edu_title or edu_title not in data.available_set:
        return html.Div(
            "Vælg en uddannelse ovenfor for at se detaljer.",
            style={
                "color": theme.muted_text,
                "fontStyle": "italic",
                "padding": "60px 20px",
                "textAlign": "center",
                "fontSize": "17px",
            }
        )

    table, providers_small = build_detail_table(data, edu_title)

    map_component = (
        build_leaflet_map(providers_small, theme)
        if not providers_small.empty
        else html.Div(
            "Ingen udbydere med koordinater",
            style={
                "height": "100%",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "color": theme.muted_text,
                "fontStyle": "italic",
            }
        )
    )

    return html.Div(
        style={
            "position": "relative",
            "background": theme.card_bg,
            "borderRadius": "12px",
            "padding": "28px",
            "boxShadow": "0 6px 24px rgba(0,0,0,0.1)",
            "border": f"1px solid {theme.card_border}",
            "overflow": "hidden",
        },
        children=[
            html.H3(
                edu_title,
                style={"margin": "0 0 24px 0", "fontSize": "24px", "fontWeight": "600", "paddingRight": "380px"},
            ),
            html.Div(table, style={"paddingRight": "400px", "boxSizing": "border-box"}),
            html.Div(
                children=[
                    html.Div(
                        "Udbud i Danmark",
                        style={
                            "position": "absolute",
                            "top": "12px",
                            "left": "14px",
                            "background": "rgba(255,255,255,0.96)",
                            "color": "#1a1a1a",
                            "padding": "6px 12px",
                            "borderRadius": "8px",
                            "fontSize": "13px",
                            "fontWeight": "600",
                            "zIndex": 100,
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
                            "pointerEvents": "none",
                        }
                    ),
                    map_component
                ],
                style={
                    "position": "absolute",
                    "top": "92px",
                    "right": "28px",
                    "width": "360px",
                    "height": "300px",
                    "borderRadius": "12px",
                    "overflow": "hidden",
                    "boxShadow": "0 12px 36px rgba(0,0,0,0.22)",
                    "zIndex": 10,
                    "border": f"2px solid {theme.card_border}",
                    "background": "white",
                }
            ),
        ]
    )

if __name__ == "__main__":
    app.run_server(debug=True)


