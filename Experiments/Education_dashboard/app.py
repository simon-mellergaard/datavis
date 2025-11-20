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
    no_update,
)
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go

from .data_loader import load_data
from .plots import (
    PARCOORD_DEFAULT_VARS,
    PARCOORD_LABELS,
    PARCOORD_VARIABLES,
    bar_colors,
    build_city_treemap,
    build_color_map_for_selected,
    build_detail_table,
    build_flow_df,
    build_parcoord_legend,
    build_parcoord_sliders,
    build_parallel_coordinates,
    build_providers_map,
    build_sankey,
)
from .theme import (
    CUSTOM_BG,
    CUSTOM_CARD,
    FONT_COL,
    MODAL_CARD_STYLE,
    MODAL_HIDDEN_STYLE,
    MODAL_VISIBLE_STYLE,
    PLOT_BG,
)

data = load_data()

ASSETS_PATH = Path(__file__).resolve().parents[2] / "Archive" / "Experiments" / "assets"
app = Dash(__name__, assets_folder=str(ASSETS_PATH))


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
                        "Fjern",
                        id=f"remove_edu{idx}",
                        n_clicks=0,
                        style={
                            "backgroundColor": "#b02a37",
                            "color": "#fff",
                            "border": "none",
                            "padding": "4px 10px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
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
                "Ingen uddannelser valgt endnu. Klik på treemap-cellerne og bekræft for at tilføje op til tre.",
                style={"color": "#adb5c6", "marginBottom": "6px"},
            ),
        )

    return rows

titles_options = [{"label": t, "value": t} for t in data.available_titles]
parcoord_available = [c for c in PARCOORD_VARIABLES if c in data.df.columns]
parcoord_default = [c for c in PARCOORD_DEFAULT_VARS if c in parcoord_available] or parcoord_available[:5]
parcoord_options = [{"label": PARCOORD_LABELS.get(c, c), "value": c} for c in parcoord_available]

app.layout = html.Div(
    style={"padding": "12px", "backgroundColor": CUSTOM_BG, "color": FONT_COL, "minHeight": "100vh"},
    children=[
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Filtrér efter kommune:", style={"marginBottom": "6px", "fontWeight": "600"}),
                                dcc.Dropdown(
                                    data.city_options,
                                    id="city_select",
                                    value="__ALL__",
                                    clearable=False,
                                    style={
                                        "marginBottom": "10px",
                                        "backgroundColor": "#1f2630",
                                        "color": FONT_COL,
                                        "border": "1px solid #2a2f3a",
                                    },
                                    className="dark-dropdown",
                                ),
                                html.Div("Vælg størrelse for klynger:", style={"marginBottom": "6px", "fontWeight": "600"}),
                                dcc.Dropdown(
                                    data.size_options,
                                    id="size_metric",
                                    value="optagne",
                                    clearable=False,
                                    style={
                                        "marginBottom": "10px",
                                        "backgroundColor": "#1f2630",
                                        "color": FONT_COL,
                                        "border": "1px solid #2a2f3a",
                                    },
                                    className="dark-dropdown",
                                ),
                            ],
                            style={**CUSTOM_CARD, "marginBottom": "10px"},
                        ),
                        dcc.Graph(id="treemap", style={"height": "620px", "width": "100%"}),
                        html.Div(
                            [
                                html.Div("Valgte uddannelser:", style={"fontWeight": "600", "marginBottom": "6px"}),
                                html.Div(
                                    render_selection_rows([None, None, None]),
                                    id="selection_summary_text",
                                    style={"marginBottom": "10px", "lineHeight": "1.5"},
                                ),
                                html.Button(
                                    "Ryd valg",
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
                            ],
                            style={**CUSTOM_CARD, "marginTop": "10px"},
                        ),
                    ],
                    style={"flex": "1 1 1100px", "minWidth": "640px"},
                ),
            ],
            style={"display": "flex", "gap": "16px", "alignItems": "flex-start", "flexWrap": "wrap"},
        ),
        html.Div(
            [
                dcc.Dropdown(titles_options, id="edu1", clearable=True),
                dcc.Dropdown(titles_options, id="edu2", clearable=True),
                dcc.Dropdown(titles_options, id="edu3", clearable=True),
            ],
            style={"display": "none"},
        ),
        html.Hr(style={"borderColor": "#2a2f3a"}),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Vælg variabler til parallelle koordinater:", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.Dropdown(
                            parcoord_options,
                            id="parcoord_vars",
                            value=parcoord_default,
                            multi=True,
                            placeholder="Vælg variabler",
                            style={
                                "marginBottom": "12px",
                                "backgroundColor": "#1f2630",
                                "color": FONT_COL,
                                "border": "1px solid #2a2f3a",
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
                                "backgroundColor": "#0f1115",
                            },
                        ),
                    ],
                    style={"flex": "4 1 0px", "minWidth": "620px", **CUSTOM_CARD},
                ),
                html.Div(
                    [
                        html.Div("Filtrer med intervaller:", style={"fontWeight": "600", "marginBottom": "6px"}),
                        html.Div(id="parcoord_sliders", style={"maxHeight": "640px", "overflowY": "auto"}),
                    ],
                    style={"flex": "1 1 220px", "minWidth": "220px", **CUSTOM_CARD},
                ),
            ],
            style={"display": "flex", "gap": "16px", "alignItems": "stretch", "flexWrap": "wrap"},
        ),
        html.Hr(style={"borderColor": "#2a2f3a"}),
        html.Div("Udforsk kandidat-retninger (vælg flere bachelorer)", style={"fontWeight": "600", "marginBottom": "6px"}),
        dcc.Dropdown(
            options=[{"label": t, "value": t} for t in data.bachelor_titles_multi],
            id="bachelor_multi",
            placeholder="Vælg en eller flere bacheloruddannelser",
            multi=True,
            clearable=True,
            style={
                "maxWidth": "900px",
                "backgroundColor": "#1f2630",
                "color": FONT_COL,
                "border": "1px solid #2a2f3a",
                "marginBottom": "14px",
            },
            className="dark-dropdown",
        ),
        html.Div(
            [
                html.Div([dcc.Graph(id="kandidat_bar", style={"height": "420px"})], style={"flex": "1 1 460px", "minWidth": "360px"}),
                html.Div([dcc.Graph(id="kandidat_flow", style={"height": "420px"})], style={"flex": "1 1 640px", "minWidth": "460px"}),
            ],
            style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
        ),
        html.Hr(style={"borderColor": "#2a2f3a"}),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Detaljer for specifik uddannelse", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.Dropdown(
                            titles_options,
                            id="detail_select",
                            placeholder="Vælg uddannelse",
                            clearable=True,
                            style={
                                "marginBottom": "10px",
                                "backgroundColor": "#1f2630",
                                "color": FONT_COL,
                                "border": "1px solid #2a2f3a",
                            },
                        ),
                        html.Div(id="detail_table", style={"overflowY": "auto"}),
                    ],
                    style={"flex": "1 1 360px", "minWidth": "320px", **CUSTOM_CARD},
                ),
                html.Div([dcc.Graph(id="detail_map", style={"height": "520px"})], style={"flex": "1 1 520px", "minWidth": "420px"}),
            ],
            style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
        ),
        dcc.Store(id="treemap_pending"),
        html.Div(
            id="treemap_modal",
            style=MODAL_HIDDEN_STYLE,
            children=[
                html.Div(
                    [
                        html.H4("Tilføj uddannelse?", style={"marginBottom": "8px"}),
                        html.Div(id="treemap_modal_label", style={"marginBottom": "16px", "fontSize": "15px"}),
                        html.Div(
                            [
                                html.Button(
                                    "Tilføj",
                                    id="treemap_confirm",
                                    style={
                                        "padding": "6px 18px",
                                        "backgroundColor": "#2b8a3e",
                                        "border": "none",
                                        "color": "#fff",
                                        "borderRadius": "4px",
                                    },
                                ),
                                html.Button(
                                    "Annullér",
                                    id="treemap_cancel",
                                    style={
                                        "padding": "6px 18px",
                                        "backgroundColor": "#b02a37",
                                        "border": "none",
                                        "color": "#fff",
                                        "borderRadius": "4px",
                                    },
                                ),
                            ],
                            style={"display": "flex", "gap": "10px", "justifyContent": "center"},
                        ),
                    ],
                    style=MODAL_CARD_STYLE,
                )
            ],
        ),
        dcc.Store(id="parcoord_color_store", data={}),
        dcc.Store(id="parcoord_filters_store", data={}),
    ],
)


@app.callback(
    Output("treemap", "figure"),
    Input("city_select", "value"),
    Input("size_metric", "value"),
    Input("edu1", "value"),
    Input("edu2", "value"),
    Input("edu3", "value"),
    Input("parcoord_filters_store", "data"),
)
def update_treemap(city_value, metric_key, e1, e2, e3, slider_filter):
    selected = [t for t in [e1, e2, e3] if t]
    slider_filter = slider_filter or {}
    return build_city_treemap(data, city_value, metric_key, selected, slider_filter)


@app.callback(
    Output("treemap_modal", "style"),
    Output("treemap_modal_label", "children"),
    Output("treemap_pending", "data"),
    Input("treemap", "clickData"),
    Input("treemap_confirm", "n_clicks"),
    Input("treemap_cancel", "n_clicks"),
    State("treemap_pending", "data"),
    prevent_initial_call=True,
)
def toggle_treemap_modal(click_data, confirm_clicks, cancel_clicks, pending):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "treemap":
        if not click_data or not click_data.get("points"):
            raise PreventUpdate
        label = click_data["points"][0].get("label")
        if not label or label not in data.available_set:
            raise PreventUpdate
        return MODAL_VISIBLE_STYLE, f"Tilføj '{label}' til sammenligningen?", label

    if trigger in {"treemap_confirm", "treemap_cancel"}:
        return MODAL_HIDDEN_STYLE, "", None

    return no_update, no_update, no_update


@app.callback(
    Output("edu1", "value"),
    Output("edu2", "value"),
    Output("edu3", "value"),
    Input("treemap_confirm", "n_clicks"),
    Input("clear_selections", "n_clicks"),
    Input("remove_edu1", "n_clicks"),
    Input("remove_edu2", "n_clicks"),
    Input("remove_edu3", "n_clicks"),
    State("treemap_pending", "data"),
    State("edu1", "value"),
    State("edu2", "value"),
    State("edu3", "value"),
    prevent_initial_call=True,
)
def modify_selections(confirm_clicks, clear_clicks, rem1, rem2, rem3, pending, v1, v2, v3):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "clear_selections":
        return None, None, None

    if trigger.startswith("remove_edu"):
        idx = int(trigger.replace("remove_edu", "")) - 1
        slots = [v1, v2, v3]
        slots.pop(idx)
        slots.append(None)
        return slots[0], slots[1], slots[2]

    if trigger == "treemap_confirm":
        if not confirm_clicks or not pending or pending not in data.available_set:
            raise PreventUpdate

        slots = [v1, v2, v3]
        if pending in slots:
            return slots

        for idx, value in enumerate(slots):
            if not value:
                slots[idx] = pending
                return slots

        slots = [slots[1], slots[2], pending]
        return slots

    raise PreventUpdate


@app.callback(Output("selection_summary_text", "children"), Input("edu1", "value"), Input("edu2", "value"), Input("edu3", "value"))
def update_selection_summary(a, b, c):
    return render_selection_rows([a, b, c])


@app.callback(
    Output("parallel_plot", "srcDoc"),
    Output("parcoord_sliders", "children"),
    Output("parcoord_color_store", "data"),
    Output("parcoord_filters_store", "data"),
    Output("parcoord_legend", "children"),
    Input("parcoord_vars", "value"),
    Input("edu1", "value"),
    Input("edu2", "value"),
    Input("edu3", "value"),
    Input({"type": "parcoord-slider", "column": ALL}, "value"),
    State({"type": "parcoord-slider", "column": ALL}, "id"),
    State("parcoord_color_store", "data"),
)
def update_parallel_plot(selected_vars, e1, e2, e3, slider_values, slider_ids, color_store):
    available = parcoord_available
    chosen = [v for v in (selected_vars or parcoord_default) if v in available]
    if not chosen:
        chosen = available[:5]

    prev_slider_values = {}
    if slider_ids and slider_values:
        prev_slider_values = {sid["column"]: val for sid, val in zip(slider_ids, slider_values)}

    slider_components, slider_filter = build_parcoord_sliders(data, chosen, prev_slider_values)
    selected_titles = [t for t in [e1, e2, e3] if t]
    color_map = build_color_map_for_selected(selected_titles, color_store)
    figure_html = build_parallel_coordinates(data, selected_titles, slider_filter, chosen, color_map)
    legend = build_parcoord_legend(selected_titles, color_map)
    return figure_html, slider_components, color_map, slider_filter, legend


@app.callback(Output("kandidat_bar", "figure"), Output("kandidat_flow", "figure"), Input("bachelor_multi", "value"))
def update_multi_charts(selected):
    empty = go.Figure()
    empty.update_layout(template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL)

    if not selected:
        return empty, empty
    chosen = [s for s in selected if s in data.bachelor_titles_multi]
    if not chosen:
        return empty, empty

    flow = build_flow_df(data, chosen)
    if flow.empty:
        return empty, empty

    agg = (
        flow.groupby("kandidat", as_index=False)
        .agg(
            {
                "weight": "sum",
                "ledighed_nyudd": "mean",
                "maanedloen_nyudd": "mean",
                "maanedloen_10aar": "mean",
            }
        )
        .sort_values("weight", ascending=False)
    )
    bar = go.Figure(
        go.Bar(
            x=agg["weight"],
            y=agg["kandidat"],
            orientation="h",
            marker=dict(color=bar_colors(len(agg))),
            hovertemplate=(
                "<b>%{y}</b><br>Vægt: %{x:.0f}<br>"
                "Ledighed (nyudd.): %{customdata[0]:.1f}<br>"
                "Løn (nyudd.): %{customdata[1]:.0f}<br>"
                "Løn (10 år): %{customdata[2]:.0f}<extra></extra>"
            ),
            customdata=np.c_[agg["ledighed_nyudd"], agg["maanedloen_nyudd"], agg["maanedloen_10aar"]],
        )
    )
    bar.update_layout(
        title="Top kandidat-retninger (samlet for valgte bachelorer)",
        template="plotly_dark",
        paper_bgcolor=CUSTOM_BG,
        plot_bgcolor=PLOT_BG,
        font_color=FONT_COL,
        margin=dict(t=50, l=10, r=20, b=40),
        yaxis=dict(automargin=True),
    )

    sankey = build_sankey(data, flow, chosen, top_k=20)
    return bar, sankey


@app.callback(Output("detail_table", "children"), Output("detail_map", "figure"), Input("detail_select", "value"))
def update_detail_panel(edu_title):
    if not edu_title or edu_title not in data.available_set:
        empty_text = html.Div("Vælg en uddannelse ovenfor for at se detaljer.", style={"color": FONT_COL})
        empty_map = go.Figure()
        empty_map.update_layout(template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL)
        return empty_text, empty_map
    table, providers_small = build_detail_table(data, edu_title)
    map_fig = build_providers_map(providers_small)
    return table, map_fig


if __name__ == "__main__":
    app.run_server(debug=True)
