import pandas as pd
import json
from io import StringIO
import requests
import re
from . import helpers


def pull_and_save_data_to_s3():
    # Getting data and normalizing
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
    deaths['countyFIPS'] = deaths['countyFIPS'].apply('{:0>5}'.format)  # Bad FIPS codes in file, add leading zeros back
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
    helpers.dataframe_to_s3(county_data, 'erik-akert-dash-public', 'coronavirus/county_data', file_type='parquet')
    s3 = helpers.open_s3fs_connection()
    with s3.open('erik-akert-dash-public/coronavirus/counties.json', 'w') as f:
        f.write(json.dumps(counties))
    return None


pull_and_save_data_to_s3()