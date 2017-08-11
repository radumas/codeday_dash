# coding: utf-8
import json

import plotly.graph_objs as go

from psycopg2 import connect
import psycopg2.sql as pgsql
import pandas
import pandas.io.sql as pandasql
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

import configparser
CONFIG = configparser.ConfigParser()
CONFIG.read('../db.cfg')
dbset = CONFIG['DBSETTINGS']
con = connect(**dbset)


app = dash.Dash()

resultid = pgsql.Literal('BR2_BR3')


weekday_avg_sql = pgsql.SQL('''
SELECT datetime_bin::TIME AS "Time", AVG(tt)
FROM bluetooth.aggr_5min
INNER JOIN bluetooth.ref_segments USING (analysis_id)
WHERE segment_name = {resultid} and EXTRACT('isodow' FROM datetime_bin) <6 AND datetime_bin >= '2017-01-01'
AND datetime_bin < '2017-02-01'
GROUP BY "Time" 
ORDER BY "Time" ''')

richmond_jan = pandasql.read_sql(weekday_avg_sql.format(resultid=resultid), con)

trace = go.Scatter(x=richmond_jan['Time'],
                   y=richmond_jan['avg'],
                   mode='lines')
layout = dict(title = "Average Weekday Travel Times",
              xaxis = dict(title="Time of Day"),
              yaxis = dict(title="Travel Time (s)"))



mapbox_token = 'pk.eyJ1IjoicmVtb3RlZ2VudHJpZnkiLCJhIjoiY2lnanJzMjJpMDA1dnYxbHo5MTZtdGZsYSJ9.gLE8d40zmDAtMSSZyd2h1Q'

geometry_sql = pgsql.SQL('''SELECT resultid, ST_ASGeoJSON(geom) geojson
FROM gis.bluetooth_routes
--FROM bluetooth.routes
WHERE resultid = {resultid} ''')

richmond_df = pandasql.read_sql(geometry_sql.format(resultid=resultid), con)

def get_lat_lon(geojson):
    lons, lats = [], []
    for coord in geojson['coordinates']:
        lons.append(coord[0])
        lats.append(coord[1])
    return lats, lons

segments = []

for row in richmond_df.itertuples():
    geojson = json.loads(row.geojson)
    lats, lons = get_lat_lon(geojson)
    segments.append(go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode='lines',
        hoverinfo='text',
        showlegend=False
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


app.layout = html.Div(children=[html.Div(dcc.Graph(id='travel-time-graph',
                                                   figure=dict(data=[trace], layout=layout))),
                                html.Div(dcc.Graph(id='bluetooth-map', 
                                                   figure=dict(data=segments, layout=map_layout)))])

if __name__ == '__main__':
    app.run_server(debug=True)


