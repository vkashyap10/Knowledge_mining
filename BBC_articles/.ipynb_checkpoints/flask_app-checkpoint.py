from flask import Flask, render_template
from bokeh.models import ColumnDataSource, Select, Slider, OpenURL, TapTool
from bokeh.resources import INLINE
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.models.callbacks import CustomJS
from datetime import date
from bokeh.io import show
from bokeh.models import CustomJS, DateRangeSlider
import pandas as pd
import numpy as np
import pandas as pd
from datetime import datetime
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, HoverTool
from bokeh.models.widgets import DateRangeSlider
from bokeh.layouts import layout, column
from bokeh.models.callbacks import CustomJS
from bokeh.plotting import figure, output_file, show, save
import numpy as np

app = Flask(__name__)

@app.route('/')
def index():
    
    # get dataframe and define bokeh object
    def selectedMovies():
        df = pd.read_csv('bbc_df.csv').reset_index()
        df = df[df['text_sentiment'].notna()]
        df = df.drop_duplicates(subset='page_url')
        
        df['list_NER'] = ''

        for index, row in df.iterrows():
            list_NERs = []
            row_ner = eval(row['NER'])
            for key in list(row_ner.keys()):
                list_NERs = list_NERs + list(np.unique(row_ner[key]))
            df.at[index,'list_NER'] = list(np.unique(list_NERs))

        res = df.to_dict('records')
        return res
    
    source = ColumnDataSource()
    currArticles = selectedMovies()
    source.data = dict(
            x = [d['index'] for d in currArticles],
            y = [d['text_sentiment'] for d in currArticles],
            color = ["#FF9900" for d in currArticles],
            heading = [d['heading'] for d in currArticles],
            date = [pd.to_datetime(d['date'], yearfirst = True) for d in currArticles],
            NER = [d['list_NER'] for d in currArticles],
            url = [d['page_url'] for d in currArticles]
        )
    
    # define controls 
    NER_list = []
    for idx in range(len(currArticles)):
        NER_list = NER_list + currArticles[idx]['list_NER']
    NER_list = list(np.unique(NER_list + ['All']))
    
    controls = {
        "min_sentiment": Slider(title="Min sentiment", value=-1, start=-1, end=1, step=0.1),
        
        "date_range_slider": DateRangeSlider(value=(date(2019, 1, 1), date(2022, 1, 1)),
                                    start=date(2019, 1, 1), end=date(2022, 1, 1)),

        "NER": Select(title="NER", value="All", options=NER_list)
    }

    controls_array = controls.values()
    
    callback = CustomJS(args=dict(source=source, controls=controls), code="""
        if (!window.full_data_save) {
            window.full_data_save = JSON.parse(JSON.stringify(source.data));
        }
    
        var full_data = window.full_data_save;
        var full_data_length = full_data.x.length;
        var new_data = { x: [], y: [], color: [], heading: [], date: [], NER: [], url: [] }
        
        for (var i = 0; i < full_data_length; i++) {
            if (full_data.y[i] === null || full_data.date[i] === null || full_data.NER[i] === null)
                continue;
            console.log((controls.date_range_slider.value[1] > full_data.date[i]) && (controls.date_range_slider.value[0] < full_data.date[i]))
            
            if (
                full_data.y[i] > controls.min_sentiment.value &&
                (controls.NER.value === 'All' || full_data.NER[i].includes(controls.NER.value, 0)) &&
                controls.date_range_slider.value[0] < full_data.date[i] &&
                controls.date_range_slider.value[1] > full_data.date[i]
            ) {
                Object.keys(new_data).forEach(key => new_data[key].push(full_data[key][i]));
            }
        }
        

        
        source.data = new_data;
        source.change.emit();
    """)

    fig = figure(plot_height=600, plot_width=720 , tooltips=[ ("Heading", "@heading"),("url", "@url") ,("NER", "@NER")])

    fig.circle(x="x", y="y", source=source, size=5, color="color", line_color=None)
    fig.xaxis.axis_label = "Articles"
    fig.yaxis.axis_label = "Sentiment"

    for single_control in controls_array:
        single_control.js_on_change('value', callback)

    inputs_column = column(*controls_array, width=320, height=1000)
    layout_row = row([ inputs_column, fig ])
    
#     url = "@url"
#     taptool = fig.select(type=TapTool)
#     taptool.callback = OpenURL(url=url)

    script, div = components(layout_row)
    return render_template(
        'index.html',
        plot_script=script,
        plot_div=div,
        js_resources=INLINE.render_js(),
        css_resources=INLINE.render_css(),
    )

if __name__ == "__main__":
    app.run(debug=True)