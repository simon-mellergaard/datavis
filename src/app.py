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
    build_providers_map,
    build_selection_bubble,
    build_treemap_drill_chart,
    build_leaflet_map,
)
from theme import CUSTOM_BG, CUSTOM_CARD, FONT_COL, get_theme

data = load_data()

ASSETS_PATH = Path(__file__).resolve().parents[0] / "assets"

app = Dash(__name__, assets_folder=str(ASSETS_PATH))

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
                        html.Div("""The plot shows the variables across all
educations in that specific city, or educations on national level. The sliders
highlight the educations that match the selected criteria, and are shown in the
bubble chart below. Hover over the name of the slider name to view details for the
likert variables. """, style={"marginBottom": "6px", "marginTop": "10px", "fontStyle": "italic"}),
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
                        html.Div("Ledighed vs karakterer (valgte uddannelser)", style={"fontWeight": "600", "marginBottom": "6px"}),
                        html.Div(id="bubble_legend", style={"marginBottom": "12px"}),
                        dcc.Graph(id="selection_bubble", style={"height": "460px"}, config=dict(displayModeBar=False)),
                        dcc.ConfirmDialog(id="bubble_confirm"),
                    ], style={"flex": "1 1 360px", "minWidth": "320px", **CUSTOM_CARD}
                ), 
                html.Div(
                    [
                        html.Div("See details for specific education", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.Dropdown(
                            titles_options,
                            id="detail_select",
                            placeholder="Vælg uddannelse",
                            clearable=True,
                            style=dropdown_style,
                            className="dark-dropdown",
                        ),
                        html.Div(id="detail_table", style={"overflowY": "auto"}),
                    ], style={"flex": "1 1 360px", "minWidth": "320px", **CUSTOM_CARD},
                ),
            ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}
        ), 
        
        
        
        html.Hr(style={"borderColor": "var(--divider)"}),

        html.Div(
            [

                html.Div(id="detail_map_container", style={"flex": "1 1 520px", "minWidth": "420px", **CUSTOM_CARD}),
            ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
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
    for metric_key, metric_label in TREEMAP_DRILL_METRICS[:4]:
        fig = build_treemap_drill_chart(data, label, metric_key, city_value, theme)
        figs.append(
            html.Div(
                dcc.Graph(figure=fig, style={"height": "260px", "width": "220px"}),
                style={"flex": "1 1 220px", "minWidth": "220px"},
            )
        )

    bbox = click_data["points"][0].get("bbox") or {}
    width = max(900, int(bbox.get("w", 900)))
    height = max(320, int(bbox.get("h", 320)))

    # Center the overlay at the midpoint of the clicked treemap cell.
    x0 = float(bbox.get("x0", width / 2))
    y0 = float(bbox.get("y0", height / 2))
    w = float(bbox.get("w", width))
    h = float(bbox.get("h", height))
    left = x0 + w / 2
    top = y0 + h / 2

    style = dict(base_style)
    style.update(
        {
            "display": "block",
            "width": f"{width}px",
            "minHeight": f"{height}px",
            "top": f"{top}px",
            "left": f"{left}px",
            "transform": "translate(-50%, -50%)",
        }
    )

    content = html.Div(
        figs,
        style={
            "display": "flex",
            "flexWrap": "wrap",
            "gap": "10px",
            "alignItems": "flex-start",
            "justifyContent": "flex-start",
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
    slider_values = args[2 + MAX_SELECTIONS] if len(args) > 2 + MAX_SELECTIONS else None
    theme_name = args[3 + MAX_SELECTIONS] if len(args) > 3 + MAX_SELECTIONS else None
    slider_ids = args[4 + MAX_SELECTIONS] if len(args) > 4 + MAX_SELECTIONS else None
    color_store = args[5 + MAX_SELECTIONS] if len(args) > 5 + MAX_SELECTIONS else None

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

    prev_slider_values = {}
    if slider_ids and slider_values:
        prev_slider_values = {sid["column"]: val for sid, val in zip(slider_ids, slider_values)}

    slider_components, slider_filter = build_parcoord_sliders(data, chosen, prev_slider_values, allowed_titles)
    selected_titles = [t for t in selections if t]
    color_map = build_color_map_for_selected(selected_titles, color_store)
    figure_html = build_parallel_coordinates(data, selected_titles, slider_filter, chosen, color_map, theme, allowed_titles)
    legend = build_parcoord_legend(selected_titles, color_map, theme)
    return figure_html, slider_components, color_map, slider_filter, legend, legend




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
    Output("detail_map_container", "children"),
    Input("detail_select", "value"),
    Input("theme_store", "data"),
)

def update_detail_panel(edu_title, theme_name):
    theme = get_theme(theme_name)
    if not edu_title or edu_title not in data.available_set:
        empty_text = html.Div("Vælg en uddannelse ovenfor for at se detaljer.", style={"color": theme.font})
        empty_map = html.Div("Ingen uddannelse valgt.", style={"color": theme.muted_text, "padding": "12px"})
        return empty_text, empty_map
    table, providers_small = build_detail_table(data, edu_title)
    leaflet_map = build_leaflet_map(providers_small, theme)
    return table, leaflet_map



if __name__ == "__main__":
    app.run_server(debug=True)


