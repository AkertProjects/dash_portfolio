import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import dash_table
import pandas as pd
import plotly.express as px
import json
from io import StringIO
import requests
import uuid
import re

# local

from app import app
from etl import helpers


def get_coronavirus_data(session_id):
    s3 = helpers.open_s3fs_connection()
    with s3.open('erik-akert-dash-public/coronavirus/counties.json', 'r') as f:
        counties = json.loads(f.read())
    county_data = helpers.get_s3_data_to_df('erik-akert-dash-public', 'coronavirus/county_data', file_type='parquet')
    return county_data, counties


def layout():
    session_id = str(uuid.uuid4())
    _layout = html.Div(children=[
        html.Div(session_id, id='session_id', style={'display': 'none'}),
        html.H1('Coronavirus USA Dashboard', style={'textAlign': 'center'}),
        html.Div(className='row', children=[
            html.Div(className='four columns', children=[
                dash_table.DataTable(id='state_data',
                                     sort_action='native',
                                     row_selectable='single',
                                     selected_rows=[],
                                     style_table={
                                         'maxHeight': '800px',
                                         'overflowY': 'scroll'
                                     }
                                     )
            ]),
            html.Div(className='eight columns', children=[
                html.Div(className='row', children=[
                    dcc.Graph(id='state_cases')
                ]),
                html.Div(className='row', children=[
                    dcc.Graph(id='county_cases')
                ])
            ])
        ])

    ])
    return _layout


@app.callback(
    [
        Output('state_data', 'columns'),
        Output('state_data', 'data'),
        Output('state_cases', 'figure')
    ],
    [
        Input('session_id', 'children')
    ]
)
def display_state_level(session_id):
    county_data, counties = get_coronavirus_data(session_id)
    most_recent_data = county_data[county_data['date'] == county_data['date'].max()]
    state_data = (most_recent_data
                  .groupby(['State', 'State Name'], as_index=False)[['Confirmed Cases', 'Deaths']].sum())
    state_fig = px.choropleth(state_data, locations='State', color='Confirmed Cases',
                              locationmode='USA-states', scope='usa', color_continuous_scale='Viridis',
                              hover_data=['State Name', 'Deaths'])
    state_fig.update_layout(title='Confirmed Cases by State')
    county_fig = px.choropleth_mapbox(most_recent_data, geojson=counties, locations='countyFIPS',
                                      color='Confirmed Cases',
                                      color_continuous_scale="Viridis",
                                      mapbox_style="carto-positron",
                                      zoom=3,
                                      center={"lat": most_recent_data['state_lat'].mean(),
                                              "lon": most_recent_data['state_lng'].mean()},
                                      hover_data=['County Name', 'State', 'Deaths'],
                                      opacity=0.5,
                                      range_color=[1, most_recent_data['Confirmed Cases'].max()]
                                      )
    county_fig.update_layout(margin={"r": 50, "t": 50, "l": 50, "b": 0}, title='Confirmed Cases by County')
    return [{'name': x, 'id': x} for x in list(state_data.to_dict().keys())], state_data.to_dict('records'), state_fig


@app.callback(
    Output('county_cases', 'figure'),
    [
        Input('session_id', 'children'),
        Input('state_data', 'derived_virtual_data'),
        Input('state_data', 'derived_virtual_selected_rows')
    ]
)
def county_map(session_id, derived_virtual_data, derived_virtual_selected_rows):
    state_selected = 'All'
    county_data, counties = get_coronavirus_data(session_id)
    most_recent_data = county_data[county_data['date'] == county_data['date'].max()]
    plot_df = most_recent_data
    zoom = 3
    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []
    if len(derived_virtual_selected_rows) > 0:
        selected_row = derived_virtual_selected_rows[0]
        state_selected = derived_virtual_data[selected_row].get('State')
        plot_df = plot_df[plot_df['State'] == state_selected]
        zoom = 4
    county_fig = px.choropleth_mapbox(plot_df, geojson=counties, locations='countyFIPS', color='Confirmed Cases',
                               color_continuous_scale="Viridis",
                               mapbox_style="carto-positron",
                               zoom=zoom,
                               center={"lat": plot_df['state_lat'].mean(), "lon": plot_df['state_lng'].mean()},
                               hover_data=['County Name', 'State', 'Deaths'],
                               opacity=0.5,
                               range_color=[1, plot_df['Confirmed Cases'].max()]
                               )
    county_fig.update_layout(margin={"r": 50, "t": 50, "l": 50, "b": 0}, title=f'Confirmed Cases by County {state_selected}')
    return county_fig

