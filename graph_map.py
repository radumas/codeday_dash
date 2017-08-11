
# coding: utf-8

from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import plotly.graph_objs as go

from psycopg2 import connect
import psycopg2.sql as pgsql
import pandas
import pandas.io.sql as pandasql
import sqlalchemy

con = connect(database='bigdata')

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

app = dash.Dash()

weekday_avg_sql = pgsql.SQL('''
SELECT updated::TIME AS "Time", AVG(timeinseconds)
FROM bluetooth.bt_2017
WHERE resultid = {resultid} and EXTRACT('isodow' FROM updated) <6
GROUP BY "Time" 
ORDER BY "Time" ''')

richmond_jan = pandasql.read_sql(weekday_avg_sql.format(resultid=pgsql.Literal('BR2_BR3')), con)

trace = go.Scatter(x=richmond_jan['Time'],
                   y=richmond_jan['avg'],
                   mode='lines')
layout = dict(title = "Average Weekday Travel Times",
              xaxis = dict(title="Time of Day"),
              yaxis = dict(title="Travel Time (s)"))

app.layout = html.Div(children=[dcc.Graph(id='travel-time-graph',
                                          figure=dict(data=[trace], layout=layout))])

if __name__ == '__main__':
    app.run_server(debug=True)


