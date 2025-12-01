"""
This script contains functions for plotting in the dashboard that are no longer
in use.
"""



def build_sankey(
    data: DataBundle,
    flow: pd.DataFrame,
    selected_bachelors: Iterable[str],
    top_k: int = 20,
    theme: Theme | None = None,
) -> go.Figure:
    theme = theme or DEFAULT_THEME
    if flow.empty:
        empty = go.Figure()
        empty.update_layout(
            template=theme.template,
            paper_bgcolor=theme.app_bg,
            plot_bgcolor=theme.plot_bg,
            font_color=theme.font,
        )
        return empty

    top = (
        flow.groupby("kandidat", as_index=False)["weight"]
        .sum()
        .sort_values("weight", ascending=False)
    )
    keep = set(top["kandidat"].head(top_k))
    filtered = flow[flow["kandidat"].isin(keep)].copy()
    if filtered.empty:
        filtered = flow.copy()

    bachelors = list(dict.fromkeys([b for b in selected_bachelors if b]))
    kandidater = sorted(filtered["kandidat"].unique())
    labels = bachelors + kandidater
    index_map = {label: idx for idx, label in enumerate(labels)}

    sources = [index_map[row["bachelor"]] for _, row in filtered.iterrows()]
    targets = [index_map[row["kandidat"]] for _, row in filtered.iterrows()]
    values = [row["weight"] for _, row in filtered.iterrows()]

    left_colors = (
        px.colors.sample_colorscale(
            px.colors.sequential.Blues_r,
            [i / max(1, len(bachelors) - 1) for i in range(len(bachelors))],
        )
        if bachelors
        else []
    )
    right_colors = (
        px.colors.sample_colorscale(
            px.colors.sequential.Blues,
            [i / max(1, len(kandidater) - 1) for i in range(len(kandidater))],
        )
        if kandidater
        else []
    )

    custom = np.c_[
        filtered["ledighed_nyudd"],
        filtered["maanedloen_nyudd"],
        filtered["maanedloen_10aar"],
    ]
    hover = (
        "<b>%{source.label}</b> → <b>%{target.label}</b><br>"
        "Vægt: %{value:.0f}<br>"
        "Ledighed (nyudd.): %{customdata[0]:.1f}%<br>"
        "Løn (nyudd.): %{customdata[1]:.0f}<br>"
        "Løn (10 år): %{customdata[2]:.0f}<extra></extra>"
    )

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=labels,
                color=left_colors + right_colors,
                pad=12,
                thickness=16,
                line=dict(color=theme.card_border, width=1),
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                customdata=custom,
                hovertemplate=hover,
            ),
        )
    )
    fig.update_layout(
        title="Flow chart: Bachelor → Kandidat (tykkelse = vægt)",
        template=theme.template,
        paper_bgcolor=theme.app_bg,
        plot_bgcolor=theme.plot_bg,
        font_color=theme.font,
        margin=dict(t=50, l=10, r=20, b=20),
        height=480,
    )
    return fig



