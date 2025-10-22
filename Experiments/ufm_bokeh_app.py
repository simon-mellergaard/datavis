# ufm_bokeh_app.py
# Run with: bokeh serve --show ufm_bokeh_app.py

from pathlib import Path
import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.models import (
    ColumnDataSource, HoverTool, Select, RangeSlider, TextInput, Div
)
from bokeh.plotting import figure
from bokeh.layouts import column, row

# -----------------------
# 1) Load & prepare data
# -----------------------
EXCEL_PATH = "../Data/DATA_UFM_combined.xlsx"

cols = [
    # INFO
    "udbud_id","titel","educational_category","displaydocclass","hovedinsttx",
    "instregiontx","instkommunetx","optagne","kvote_1_kvotient",
    # LIKERT
    "fagligmiljo_likert","arbmedstud_likert","medstuderende_likert",
    "udbytte_undervisning_likert","socialtmiljo_likert","ensom_likert",
    "stress_daglig_likert","tilpas_likert","undervisere_engagerede_likert",
    "undervisere_feedback_likert","undervisere_hjaelp_likert","undervisere_kontakt_likert",
    "ruster_til_job_likert","relevans_overens_udd_job_likert",
    # CONTINUOUS
    "afbrud","tidsforbrug_p50","tidsforbrug_arbejde",
    "uddaktivitet_opgaver_pct","uddaktivitet_praktik_pct",
    "uddaktivitet_udlandsophold_pct","uddaktivitet_undervisning_pct",
    "undervisningsform_p1",
    # JOB
    "arbejdstid_timer","ledighed_nyudd","maanedloen_nyudd","maanedloen_10aar",
]

# Read data
df_raw = pd.read_excel(EXCEL_PATH, header=0)
data = df_raw[cols].copy()

# Remove national-level rows and udbud_id; drop rows with any NA
data = data[data["udbud_id"] != 999999].drop(columns=["udbud_id"]).dropna()

# ✅ Ensure unique column names (avoid DataFrame return on data[c])
if data.columns.duplicated().any():
    seen = {}
    new_cols = []
    for c in data.columns:
        if c not in seen:
            seen[c] = 1
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
    data.columns = new_cols

# Ensure numeric dtypes for all Likert/GPA candidates
likert_candidates = [
    "fagligmiljo_likert","arbmedstud_likert","medstuderende_likert",
    "udbytte_undervisning_likert","socialtmiljo_likert","ensom_likert",
    "stress_daglig_likert","tilpas_likert","undervisere_engagerede_likert",
    "undervisere_feedback_likert","undervisere_hjaelp_likert","undervisere_kontakt_likert",
    "ruster_til_job_likert","relevans_overens_udd_job_likert",
]
for c in likert_candidates + ["kvote_1_kvotient"]:
    if c in data.columns:
        data[c] = pd.to_numeric(data[c], errors="coerce")

# -----------------------
# 2) Widgets
# -----------------------
default_likert = "fagligmiljo_likert" if "fagligmiljo_likert" in data.columns else likert_candidates[0]
likert_select = Select(
    title="Likert column",
    value=default_likert,
    options=[c for c in likert_candidates if c in data.columns]
)

def likert_range_bounds(col: str):
    x = data[col].dropna().astype(float)
    if x.empty:
        return 0.0, 1.0
    lo, hi = float(x.min()), float(x.max())
    # If looks like Likert, clamp/round to 1..5
    if lo >= 1 and hi <= 5:
        lo = max(1.0, float(np.floor(lo)))
        hi = min(5.0, float(np.ceil(hi)))
    return lo, hi

lo0, hi0 = likert_range_bounds(default_likert)
likert_slider = RangeSlider(
    title="Likert min–max",
    value=(lo0, hi0),
    start=lo0,
    end=hi0,
    step=1.0 if hi0 - lo0 <= 10 else 0.5
)

gpa_input = TextInput(title="Minimum GPA (optional, e.g., 9 — leave blank to disable)", value="")

summary_div = Div(text="", width=420)

# -----------------------
# 3) Data sources & plot
# -----------------------
source_all = ColumnDataSource(data)
source_view = ColumnDataSource({k: [] for k in data.columns})  # will be filled by filter()

p = figure(
    width=820, height=540,
    title="Stress vs Loneliness by Educational Program",
    x_axis_label="Daily Stress (Likert)",
    y_axis_label="Loneliness (Likert)",
    tools="pan,wheel_zoom,box_zoom,reset,save"
)

r = p.circle(
    x="stress_daglig_likert",
    y="ensom_likert",
    size=8,
    alpha=0.6,
    source=source_view
)

hover = HoverTool(tooltips=[
    ("Program", "@titel"),
    ("Stress", "@stress_daglig_likert{0.0}"),
    ("Loneliness", "@ensom_likert{0.0}")
])
p.add_tools(hover)

# -----------------------
# 4) Callbacks
# -----------------------
def parse_gpa(txt):
    txt = (txt or "").strip()
    if txt == "":
        return None
    try:
        return float(txt.replace(",", "."))
    except ValueError:
        return None

def apply_filter():
    col = likert_select.value
    lo, hi = likert_slider.value
    gpa_min = parse_gpa(gpa_input.value)

    df = data.copy()
    # Likert filter
    df = df[(df[col] >= lo) & (df[col] <= hi)]
    # GPA filter (optional)
    if gpa_min is not None and "kvote_1_kvotient" in df.columns:
        df = df[df["kvote_1_kvotient"] >= gpa_min]

    # Update the view source
    source_view.data = {k: df[k].values for k in df.columns}

    # Update summary
    summary_div.text = (
        f"<b>Rows after filter:</b> {len(df)} / {len(data)}<br>"
        f"<b>Likert column:</b> {col} in [{lo}, {hi}]<br>"
        + (f"<b>GPA ≥</b> {gpa_min}" if gpa_min is not None else "<i>GPA filter off</i>")
    )

def on_likert_change(attr, old, new):
    lo, hi = likert_range_bounds(new)
    # Reset slider bounds & value to the new column's range
    likert_slider.start = lo
    likert_slider.end = hi
    likert_slider.value = (lo, hi)
    apply_filter()

def on_slider_change(attr, old, new):
    apply_filter()

def on_gpa_change(attr, old, new):
    apply_filter()

likert_select.on_change("value", on_likert_change)
likert_slider.on_change("value", on_slider_change)
gpa_input.on_change("value", on_gpa_change)

# Initial compute
apply_filter()

# -----------------------
# 5) Layout
# -----------------------
controls = column(likert_select, likert_slider, gpa_input, summary_div, sizing_mode="fixed")
layout = row(controls, p, sizing_mode="stretch_width")
curdoc().add_root(layout)
curdoc().title = "UFM Filter (Bokeh)"