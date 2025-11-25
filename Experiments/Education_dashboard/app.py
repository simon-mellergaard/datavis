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
from .theme import CUSTOM_BG, CUSTOM_CARD, FONT_COL, get_theme

data = load_data()

ASSETS_PATH = Path(__file__).resolve().parents[2] / "Archive" / "Experiments" / "assets"
app = Dash(__name__, assets_folder=str(ASSETS_PATH))
TREEMAP_PROMPT = "Klik pÃ¥ treemap-cellerne for at vÃ¦lge en uddannelse."


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
                "Ingen uddannelser valgt endnu. Klik pÃ¥ treemap-cellerne og bekrÃ¦ft for at tilfÃ¸je op til tre.",
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
}

app.layout = html.Div(
    style={"padding": "12px", "backgroundColor": CUSTOM_BG, "color": FONT_COL, "minHeight": "100vh"},
    children=[
        dcc.Store(id="theme_store", data="dark", storage_type="local"),
        html.Div(
            [
                html.Div("Mørkt tema", id="theme_status", style={"fontSize": "14px", "color": "var(--muted-text)"}),
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
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("FiltrÃ©r efter kommune:", style={"marginBottom": "6px", "fontWeight": "600"}),
                                dcc.Dropdown(
                                    data.city_options,
                                    id="city_select",
                                    value="__ALL__",
                                    clearable=False,
                                    style=dropdown_style,
                                    className="dark-dropdown",
                                ),
                                html.Div("VÃ¦lg stÃ¸rrelse for klynger:", style={"marginBottom": "6px", "fontWeight": "600"}),
                                dcc.Dropdown(
                                    data.size_options,
                                    id="size_metric",
                                    value="optagne",
                                    clearable=False,
                                    style=dropdown_style,
                                    className="dark-dropdown",
                                ),
                            ],
                            style={**CUSTOM_CARD, "marginBottom": "10px"},
                        ),
                        dcc.Graph(id="treemap", style={"height": "620px", "width": "100%"}),
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
                                            "TilfÃ¸j til sammenligning",
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
        html.Hr(style={"borderColor": "var(--divider)"}),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("VÃ¦lg variabler til parallelle koordinater:", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.Dropdown(
                            parcoord_options,
                            id="parcoord_vars",
                            value=parcoord_default,
                            multi=True,
                            placeholder="VÃ¦lg variabler",
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
                        html.Div("Filtrer med intervaller:", style={"fontWeight": "600", "marginBottom": "6px"}),
                        html.Div(id="parcoord_sliders", style={"maxHeight": "640px", "overflowY": "auto"}),
                    ],
                    style={"flex": "1 1 220px", "minWidth": "220px", **CUSTOM_CARD},
                ),
            ],
            style={"display": "flex", "gap": "16px", "alignItems": "stretch", "flexWrap": "wrap"},
        ),
        html.Hr(style={"borderColor": "var(--divider)"}),
        html.Div("Udforsk kandidat-retninger (vÃ¦lg flere bachelorer)", style={"fontWeight": "600", "marginBottom": "6px"}),
        dcc.Dropdown(
            options=[{"label": t, "value": t} for t in data.bachelor_titles_multi],
            id="bachelor_multi",
            placeholder="VÃ¦lg en eller flere bacheloruddannelser",
            multi=True,
            clearable=True,
            style={
                "maxWidth": "900px",
                "backgroundColor": "var(--control-bg)",
                "color": FONT_COL,
                "border": "1px solid var(--control-border)",
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
        html.Hr(style={"borderColor": "var(--divider)"}),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Detaljer for specifik uddannelse", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.Dropdown(
                            titles_options,
                            id="detail_select",
                            placeholder="VÃ¦lg uddannelse",
                            clearable=True,
                            style={
                                "marginBottom": "10px",
                                "backgroundColor": "var(--control-bg)",
                                "color": FONT_COL,
                                "border": "1px solid var(--control-border)",
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
        dcc.Store(id="parcoord_color_store", data={}),
        dcc.Store(id="parcoord_filters_store", data={}),
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
        const buttonLabel = mode === 'light' ? 'Skift til mørk tilstand' : 'Skift til lys tilstand';
        const statusLabel = mode === 'light' ? 'Lyst tema' : 'Mørkt tema';
        return [buttonLabel, statusLabel];
    }
    """,
    Output("theme_toggle", "children"),
    Output("theme_status", "children"),
    Input("theme_store", "data"),
)


@app.callback(
    Output("treemap", "figure"),
    Input("city_select", "value"),
    Input("size_metric", "value"),
    Input("edu1", "value"),
    Input("edu2", "value"),
    Input("edu3", "value"),
    Input("parcoord_filters_store", "data"),
    Input("theme_store", "data"),
)
def update_treemap(city_value, metric_key, e1, e2, e3, slider_filter, theme_name):
    theme = get_theme(theme_name)
    selected = [t for t in [e1, e2, e3] if t]
    slider_filter = slider_filter or {}
    return build_city_treemap(data, city_value, metric_key, selected, slider_filter, theme)


@app.callback(
    Output("treemap_pending", "data"),
    Output("treemap_pending_label", "children"),
    Output("treemap_add", "disabled"),
    Input("treemap", "clickData"),
)
def capture_treemap_selection(click_data):
    if not click_data or not click_data.get("points"):
        return None, TREEMAP_PROMPT, True
    label = click_data["points"][0].get("label")
    if not label or label not in data.available_set:
        return None, TREEMAP_PROMPT, True
    msg = f"Valgt uddannelse: {label}. Klik pÃ¥ 'TilfÃ¸j til sammenligning' for at fremhÃ¦ve den."
    return label, msg, False


@app.callback(
    Output("edu1", "value"),
    Output("edu2", "value"),
    Output("edu3", "value"),
    Input("treemap_add", "n_clicks"),
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
def modify_selections(add_clicks, clear_clicks, rem1, rem2, rem3, pending, v1, v2, v3):
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

    if trigger == "treemap_add":
        if not add_clicks or not pending or pending not in data.available_set:
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
    Input("theme_store", "data"),
    State({"type": "parcoord-slider", "column": ALL}, "id"),
    State("parcoord_color_store", "data"),
)
def update_parallel_plot(selected_vars, e1, e2, e3, slider_values, theme_name, slider_ids, color_store):
    theme = get_theme(theme_name)
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
    figure_html = build_parallel_coordinates(data, selected_titles, slider_filter, chosen, color_map, theme)
    legend = build_parcoord_legend(selected_titles, color_map, theme)
    return figure_html, slider_components, color_map, slider_filter, legend


@app.callback(
    Output("kandidat_bar", "figure"),
    Output("kandidat_flow", "figure"),
    Input("bachelor_multi", "value"),
    Input("theme_store", "data"),
)
def update_multi_charts(selected, theme_name):
    theme = get_theme(theme_name)
    empty = go.Figure()
    empty.update_layout(template=theme.template, paper_bgcolor=theme.app_bg, plot_bgcolor=theme.plot_bg, font_color=theme.font)

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
                "<b>%{y}</b><br>VÃ¦gt: %{x:.0f}<br>"
                "Ledighed (nyudd.): %{customdata[0]:.1f}<br>"
                "LÃ¸n (nyudd.): %{customdata[1]:.0f}<br>"
                "LÃ¸n (10 Ã¥r): %{customdata[2]:.0f}<extra></extra>"
            ),
            customdata=np.c_[agg["ledighed_nyudd"], agg["maanedloen_nyudd"], agg["maanedloen_10aar"]],
        )
    )
    bar.update_layout(
        title="Top kandidat-retninger (samlet for valgte bachelorer)",
        template=theme.template,
        paper_bgcolor=theme.app_bg,
        plot_bgcolor=theme.plot_bg,
        font_color=theme.font,
        margin=dict(t=50, l=10, r=20, b=40),
        yaxis=dict(automargin=True),
    )

    sankey = build_sankey(data, flow, chosen, top_k=20, theme=theme)
    return bar, sankey


@app.callback(
    Output("detail_table", "children"),
    Output("detail_map", "figure"),
    Input("detail_select", "value"),
    Input("theme_store", "data"),
)
def update_detail_panel(edu_title, theme_name):
    theme = get_theme(theme_name)
    if not edu_title or edu_title not in data.available_set:
        empty_text = html.Div("VÃ¦lg en uddannelse ovenfor for at se detaljer.", style={"color": theme.font})
        empty_map = go.Figure()
        empty_map.update_layout(template=theme.template, paper_bgcolor=theme.app_bg, plot_bgcolor=theme.plot_bg, font_color=theme.font)
        return empty_text, empty_map
    table, providers_small = build_detail_table(data, edu_title)
    map_fig = build_providers_map(providers_small, theme)
    return table, map_fig


if __name__ == "__main__":
    app.run_server(debug=True)







