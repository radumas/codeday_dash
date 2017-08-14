# coding: utf-8
import json
import itertools
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

resultids = pgsql.Literal(['BR1_BR2', 'BR2_BR3', 'BR3_BR4'])

weekday_avg_sql = pgsql.SQL('''
WITH agg AS(SELECT segment_id, start_road ||': ' || start_crossstreet ||' to '||end_crossstreet as segment_name, 
datetime_bin::TIME AS "Time", AVG(tt)::INT
FROM bluetooth.aggr_5min
INNER JOIN bluetooth.ref_segments USING (analysis_id)
WHERE ARRAY[segment_name::TEXT] <@ {resultids} and EXTRACT('isodow' FROM datetime_bin) <6 AND datetime_bin >= '2017-01-01'
AND datetime_bin < '2017-02-01'
GROUP BY segment_id, segment_name, "Time" )

SELECT * 
FROM agg
RIGHT OUTER JOIN (SELECT (generate_series(0,287) * interval '5 minutes')::TIME "Time") t using ("Time")
ORDER BY segment_id, "Time"''')
print('Loading Data')
weekday_avg = pandasql.read_sql(weekday_avg_sql.format(resultids=resultids), con)


mapbox_token = 'pk.eyJ1IjoicmVtb3RlZ2VudHJpZnkiLCJhIjoiY2lnanJzMjJpMDA1dnYxbHo5MTZtdGZsYSJ9.gLE8d40zmDAtMSSZyd2h1Q'



geometry_sql = pgsql.SQL('''SELECT resultid, segment_id, start_road as segment_name, ST_ASGeoJSON(geom) geojson
FROM gis.bluetooth_routes
INNER JOIN bluetooth.ref_segments ON resultid = segment_name
--FROM bluetooth.routes
WHERE ARRAY[resultid::TEXT] <@ {resultids} ''')

map_data = pandasql.read_sql(geometry_sql.format(resultids=resultids), con)

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
        name=row.segment_name,
        customdata=list(itertools.repeat(row.segment_id, times=len(lats))),
        text=row.segment_name,
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

                                


app.layout = html.Div(children=[html.Div(html.H2('Click on a segment to view average travel times for it.')),
                                html.Div(dcc.Graph(id='bluetooth-map', 
                                                   figure=dict(data=segments, layout=map_layout))),
#                                html.Pre(id='click-data', style={'border': 'thin lightgrey solid'}),
                                html.Div(dcc.Graph(id='travel-time-graph'))
                                ])
#@app.callback(
#    Output('click-data', 'children'),
#    [Input('bluetooth-map', 'clickData')])
#def print_click_data(click_data):
#    segment_id = 63
#    if click_data is not None:
#        segment_id = click_data['points'][0]['customdata']
#    segment_name = weekday_avg[weekday_avg['segment_id'] ==  segment_id].iloc[[0]]['segment_name']
#    return str(segment_id) +': ' + segment_name

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


