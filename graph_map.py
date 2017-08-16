# coding: utf-8
import json
import itertools
import os

import plotly.graph_objs as go

from psycopg2 import connect
import psycopg2.sql as pgsql
import pandas
import pandas.io.sql as pandasql
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

database_url = os.getenv("DATABASE_URL")
if database_url is not None:
    con = connect(database_url)
else:
    import configparser
    CONFIG = configparser.ConfigParser()
    CONFIG.read('../db.cfg')
    dbset = CONFIG['DBSETTINGS']
    con = connect(**dbset)

app = dash.Dash()
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True
server = app.server
server.secret_key = os.environ.get('SECRET_KEY', 'my-secret-key')

weekday_avg = pandasql.read_sql('SELECT * FROM bluetooth_avg_jan', con)

mapbox_token = 'pk.eyJ1IjoicmVtb3RlZ2VudHJpZnkiLCJhIjoiY2lnanJzMjJpMDA1dnYxbHo5MTZtdGZsYSJ9.gLE8d40zmDAtMSSZyd2h1Q'

geometry_sql = pgsql.SQL('''SELECT segment_name, segment_id,  ST_ASGeoJSON(geom) geojson
FROM bluetooth_routes ''')

map_data = pandasql.read_sql(geometry_sql, con)

def get_lat_lon(geojson):
    lons, lats = [], []
    for coord in geojson['coordinates']:
        lons.append(coord[0])
        lats.append(coord[1])
    return lats, lons

segments = []

for row in map_data.itertuples():
    geojson = json.loads(row.geojson)
    lats, lons = get_lat_lon(geojson)
    segments.append(go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode='lines',
        hoverinfo='name',
        customdata=list(itertools.repeat(row.segment_id, times=len(lats))),
        name=row.segment_name,
        showlegend=False,
        line=dict(color='#004B85')
    ))
    
map_layout = go.Layout(
    title='Bluetooth Segments',
    autosize=True,
    hovermode='closest',
    mapbox=dict(
        accesstoken=mapbox_token,
        bearing=0,
        center=dict(
            lat=43.65,
            lon=-79.37
        ),
        pitch=0,
        zoom=12,
        style='light'
    )
)    

app.layout = html.Div(children=[html.Div(html.H2('Click on a segment to view average travel times for it.')),
                                html.Div(dcc.Graph(id='bluetooth-map', 
                                                   figure=dict(data=segments, layout=map_layout))),
                                html.Div(dcc.Graph(id='travel-time-graph'))
                                ])

@app.callback(
    Output('travel-time-graph', 'figure'),
    [Input('bluetooth-map', 'clickData')])
def update_graph(segment):
    segment_id = None
    if segment is None:
        segment_id = 63
    else:
        segment_id = segment['points'][0]['customdata']
                                
    filtered_data = weekday_avg[weekday_avg['segment_id'] ==  segment_id]
    
    title = filtered_data.iloc[0]['segment_name']
    
    
    data = [go.Scatter(x=filtered_data['Time'],
                   y=filtered_data['avg'],
                   mode='lines')]
    layout = dict(title = 'Average Weekday Travel Times <br>' +title,
                  xaxis = dict(title="Time of Day"),
                  yaxis = dict(title="Travel Time (s)"))
    
    return {'data':data, 'layout':layout}

if __name__ == '__main__':
    app.run_server(debug=True)


