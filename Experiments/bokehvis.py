# create a complex chart with mouse-over tooltips

from bokeh.palettes import HighContrast3
from bokeh.plotting import figure, show
from bokeh.models import TextInput
from bokeh.layouts import layout
from bokeh.io import curdoc



fruits = ["Apples", "Pears", "Nectarines", "Plums", "Grapes", "Strawberries"]
years = ["2015", "2016", "2017"]

data = {
    "fruits": fruits,
    "2015": [2, 1, 4, 3, 2, 4],
    "2016": [5, 3, 4, 2, 4, 6],
    "2017": [3, 2, 4, 4, 5, 3]
}

p = figure(
    x_range=fruits,
    height=250,
    title="Fruit Counts by Year",
    toolbar_location=None,
    tools="hover",
    tooltips="$name @fruits: @$name"
)

p.vbar_stack(years, x="fruits", width=0.9, color=HighContrast3, source=data, legend_label=years)

p.y_range.start = 0
p.x_range.range_padding = 0.1
p.xgrid.grid_line_color = None
p.axis.minor_tick_line_color = None
p.outline_line_color = None
p.legend.location = "top_left"
p.legend.orientation = "horizontal"

textinput = TextInput(value="Type here", title="Label:")

layout = layout([textinput], [p])

# show(layout)
# show(p)

# set up the ui for the server
curdoc().add_root(layout)
curdoc().title = "Fruit Counts"


# run with: bokeh serve --show bokehvis.py


# then go to http://localhost:5006/bokehvis to see the result
# to stop the server, go to the terminal and hit Ctrl-C
# to restart the server, hit the up arrow and Enter

# to deploy the server, see https://docs.bokeh.org/en/latest/docs/user_guide/server.html#deployment
# for example, using heroku: https://devcenter.heroku.com/articles/getting-started-with-python#introduction
# or using a cloud service: https://docs.bokeh.org/en/latest/docs/user_guide/server.html#cloud-services
# or using docker: https://hub.docker.com/r/bokeh/bokeh

