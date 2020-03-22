import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import dash_table
import pandas as pd
import plotly.express as px
import json

# local

from app import app
from app import cache


def layout():
    confirmed_cases = pd.read_csv('./data/covid_confirmed_usafacts.csv', encoding='latin', dtype=str)
    deaths = pd.read_csv('./data/covid_deaths_usafacts.csv', dtype=str)
    states = pd.read_csv('./data/states.csv')
    confirmed_cases['countyFIPS'] = confirmed_cases['countyFIPS'].apply(
        '{:0>5}'.format)  # Bad FIPS codes in file, add leading zeros back
    deaths['countyFIPS'] = deaths['countyFIPS'].apply('{:0>5}'.format)  # Bad FIPS codes in file, add leading zeros back
    confirmed_melted = pd.melt(confirmed_cases, id_vars=['countyFIPS', 'County Name', 'State'],
                               value_vars=list(confirmed_cases.columns[4:]),
                               var_name='date', value_name='Confirmed Cases')
    deaths_melted = pd.melt(deaths, id_vars=['countyFIPS', 'County Name', 'State'], value_vars=list(deaths.columns[4:]),
                            var_name='date', value_name='Deaths')
    county_data = pd.merge(confirmed_melted, deaths_melted, on=['countyFIPS', 'date', 'County Name', 'State'],
                           how='outer').fillna(0.0)
    county_data = county_data[
        (~county_data['County Name'].str.contains('Unallocated'))
    ]
    county_data[['Confirmed Cases', 'Deaths']] = county_data[['Confirmed Cases', 'Deaths']].astype(int)
    county_data['date'] = pd.to_datetime(county_data['date'])
    county_data = pd.merge(county_data, states, on='State').rename(columns={'lat': 'state_lat', 'lng': 'state_lng'})
    most_recent_data = county_data[county_data['date'] == county_data['date'].max()]
    state_data = (most_recent_data
                  .groupby(['State', 'State Name'], as_index=False)[['Confirmed Cases', 'Deaths']].sum())
    counties = json.loads(open('./data/geojson-counties-fips.json', 'r').read())
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
    _layout = html.Div(children=[
        html.Div(className='four columns', children=[
            dash_table.DataTable(id='state_data',
                                 columns=[{'name': x, 'id': x} for x in list(state_data.to_dict().keys())],
                                 data=state_data.to_dict('records'))
        ]),
        html.Div(className='eight columns', children=[
            html.Div(className='row', children=[
                dcc.Graph(id='state_cases', figure=state_fig)
            ]),
            html.Div(className='row', children=[
                dcc.Graph(id='county_cases', figure=county_fig)
            ])
        ])
    ])
    return _layout

# @app.callback(
#     Output('county_cases', 'figure'),
#     [
#         Input()
#     ]
# )
