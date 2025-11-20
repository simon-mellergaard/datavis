from __future__ import annotations

from pathlib import Path

import numpy as np
from dash import (
    Dash,
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
    bar_colors,
    build_city_treemap,
    build_detail_table,
    build_flow_df,
    build_providers_map,
    build_radar_raw,
    build_sankey,
    build_simple_bar,
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

titles_options = [{"label": t, "value": t} for t in data.available_titles]

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
                                html.Div(id="selection_summary_text", style={"marginBottom": "10px", "lineHeight": "1.5"}),
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
                html.Div([dcc.Graph(id="radar", style={"height": "560px"})], style={"flex": "3 1 0px", "minWidth": "520px"}),
                html.Div(
                    [
                        html.Div(id="bachelor_notice", style={**CUSTOM_CARD, "display": "none", "marginBottom": "8px"}),
                        dcc.Graph(id="bar_afbrud", style={"height": "200px", "marginBottom": "10px"}),
                        dcc.Graph(id="bar_ledighed", style={"height": "200px", "marginBottom": "10px"}),
                        dcc.Graph(id="bar_loen_ny", style={"height": "200px"}),
                    ],
                    style={"flex": "2 1 0px", **CUSTOM_CARD},
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
    ],
)


@app.callback(
    Output("treemap", "figure"),
    Input("city_select", "value"),
    Input("size_metric", "value"),
    Input("edu1", "value"),
    Input("edu2", "value"),
    Input("edu3", "value"),
)
def update_treemap(city_value, metric_key, e1, e2, e3):
    selected = [t for t in [e1, e2, e3] if t]
    return build_city_treemap(data, city_value, metric_key, selected)


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
    State("treemap_pending", "data"),
    State("edu1", "value"),
    State("edu2", "value"),
    State("edu3", "value"),
    prevent_initial_call=True,
)
def modify_selections(confirm_clicks, clear_clicks, pending, v1, v2, v3):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "clear_selections":
        return None, None, None

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
    selected = [t for t in [a, b, c] if t]
    if not selected:
        return html.Div(
            "Ingen uddannelser valgt endnu. Klik på treemap-cellerne og bekræft for at tilføje op til tre.",
            style={"color": "#adb5c6"},
        )
    return html.Div([html.Div(f"{idx + 1}. {title}") for idx, title in enumerate(selected)])


@app.callback(
    Output("radar", "figure"),
    Output("bachelor_notice", "children"),
    Output("bachelor_notice", "style"),
    Output("bar_afbrud", "figure"),
    Output("bar_ledighed", "figure"),
    Output("bar_loen_ny", "figure"),
    Input("edu1", "value"),
    Input("edu2", "value"),
    Input("edu3", "value"),
)
def update_main(a, b, c):
    selected = [x for x in [a, b, c] if x in data.available_set]
    radar_fig = build_radar_raw(data, selected)

    notice_titles = []
    for title in selected:
        row = data.df[data.df["titel"] == title]
        if not row.empty and str(row.iloc[0]["displaydocclass"]) == "Bacheloruddannelse":
            notice_titles.append(title)
    if notice_titles:
        message = html.Div(
            [
                html.Div("Bemærk:", style={"fontWeight": "700", "marginBottom": "4px"}),
                html.Div(
                    "Du har valgt en universitets-bachelor: "
                    + ", ".join(notice_titles)
                    + ". Yderligere uddannelse (kandidat) kan være nødvendig. Brug værktøjet nedenfor til at se relevante kandidatuddannelser.",
                    style={"lineHeight": "1.5"},
                ),
            ]
        )
        style = {**CUSTOM_CARD, "display": "block", "borderLeft": "4px solid #4C9BE8"}
    else:
        message = ""
        style = {**CUSTOM_CARD, "display": "none"}

    bar_afbrud = build_simple_bar(data, "afbrud", selected, "Afbrud (%)")
    bar_ledighed = build_simple_bar(data, "ledighed_nyudd", selected, "Ledighed (nyudd.) (%)")
    bar_loen_ny = build_simple_bar(data, "maanedloen_nyudd", selected, "Løn (nyudd.)", tickprefix="kr ")

    return radar_fig, message, style, bar_afbrud, bar_ledighed, bar_loen_ny


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
