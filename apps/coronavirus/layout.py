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
from app import cache


def get_coronavirus_data(session_id):
    @cache.memoize()
    def pull_and_serialize_data(session_id):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}
        confirmed_cases = pd.read_csv(
            StringIO(requests.get('https://static.usafacts.org/public/data/covid-19/covid_confirmed_usafacts.csv',
                                  headers=headers).text))
        confirmed_cases.columns = [re.findall(r'[A-Za-z0-9//\s]+', x)[0] for x in
                                   confirmed_cases.columns]  # Weird column names coming through, encoding does not fix
        deaths = pd.read_csv(
            StringIO(requests.get('https://static.usafacts.org/public/data/covid-19/covid_deaths_usafacts.csv',
                                  headers=headers).text), encoding='utf8')
        deaths.columns = [re.findall(r'[A-Za-z0-9//\s]+', x)[0] for x in
                          deaths.columns]  # Weird column names coming through, encoding does not fix
        confirmed_cases['countyFIPS'] = confirmed_cases['countyFIPS'].apply(
            '{:0>5}'.format)  # Bad FIPS codes in file, add leading zeros back
        deaths['countyFIPS'] = deaths['countyFIPS'].apply(
            '{:0>5}'.format)  # Bad FIPS codes in file, add leading zeros back
        states = pd.read_csv('./data/states.csv')
        counties = json.loads(open('./data/geojson-counties-fips.json', 'r').read())
        confirmed_melted = pd.melt(confirmed_cases, id_vars=['countyFIPS', 'County Name', 'State'],
                                   value_vars=list(confirmed_cases.columns[4:]),
                                   var_name='date', value_name='Confirmed Cases')
        deaths_melted = pd.melt(deaths, id_vars=['countyFIPS', 'County Name', 'State'],
                                value_vars=list(deaths.columns[4:]),
                                var_name='date', value_name='Deaths')
        county_data = pd.merge(confirmed_melted, deaths_melted, on=['countyFIPS', 'date', 'County Name', 'State'],
                               how='outer').fillna(0.0)
        county_data[['Confirmed Cases', 'Deaths']] = county_data[['Confirmed Cases', 'Deaths']].astype(int)
        county_data['date'] = pd.to_datetime(county_data['date'])
        county_data = pd.merge(county_data, states, on='State').rename(columns={'lat': 'state_lat', 'lng': 'state_lng'})
        return county_data.to_json(date_format='iso'), counties

    county_data_json, counties = pull_and_serialize_data(session_id)
    county_data = pd.read_json(county_data_json, dtype={'countyFIPS': str})
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
                                         'maxHeight': '1026px',
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

