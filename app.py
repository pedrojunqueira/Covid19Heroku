import io
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objs as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go


app = dash.Dash()
server = app.server

url_confirmed = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'
url_deaths = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'
url_recovered = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv'

urls = [url_confirmed, url_deaths, url_recovered]
series = ['confirmed', 'deaths', 'recovered']
ids = ['Province/State', 'Country/Region', 'Lat', 'Long']

for url, serie in zip(urls, series):
    r = requests.get(url).content
    df = pd.read_csv(io.StringIO(r.decode('utf-8')))
    df = df.melt(id_vars=ids)
    df.rename(columns={'variable': 'date', 'value': serie}, inplace=True)
    df.loc[:, 'date'] = df['date'].apply(
        lambda x: datetime.strptime(x, '%m/%d/%y'))
    df.to_csv(f'{serie}.csv', index=False)


def active_country(country):

    confirmed = pd.read_csv('confirmed.csv')
    deaths = pd.read_csv('deaths.csv')
    recovered = pd.read_csv('recovered.csv')
    confirmed_region = confirmed[confirmed['Country/Region'] == country]
    deaths_region = deaths[deaths['Country/Region'] == country]
    recovered_region = recovered[recovered['Country/Region'] == country]
    confirmed_region = confirmed_region.pivot_table(
        index=['date', 'Country/Region'], values='confirmed', aggfunc='sum')
    deaths_region = deaths_region.pivot_table(
        index=['date', 'Country/Region'], values='deaths', aggfunc='sum')
    recovered_region = recovered_region.pivot_table(
        index=['date', 'Country/Region'], values='recovered', aggfunc='sum')
    confirmed_region.reset_index(level=1, inplace=True)
    deaths_region.reset_index(level=1, inplace=True)
    recovered_region.reset_index(level=1, inplace=True)
    active_region = confirmed_region.copy()
    active_region = active_region.join(recovered_region.loc[:, ['recovered']])
    active_region = active_region.join(deaths_region.loc[:, ['deaths']])
    active_region.loc[:, 'active'] = active_region['confirmed'] - \
        active_region['recovered'] - active_region['deaths']
    active_region.loc[:, 'confirmed_pd'] = active_region['confirmed'].shift(1)
    active_region.loc[:, 'new_cases'] = active_region['confirmed'] - \
        active_region['confirmed_pd']
    active_region.loc[:, 'growth'] = active_region['confirmed'] / \
        active_region['confirmed_pd']
    active_region.loc[:, 'new_cases_pd'] = active_region['new_cases'].shift(1)
    active_region.loc[:, 'growth_factor'] = active_region['new_cases'] / \
        active_region['new_cases_pd']
    return active_region


country_data = pd.read_csv('confirmed.csv')

country_options = []
for country in country_data['Country/Region'].unique():
    country_options.append({'label': country, 'value': country})


app.layout = html.Div([
    html.H2(children='How each country are winning Covid-19',
            style={'text-align': 'center'}),

    html.Div([
        dcc.Graph(id='graph1')], style={'width': '48%',  'display': 'inline-block'}),
    html.Div([
        dcc.Graph(id='graph2')], style={'width': '48%', 'float': 'right', 'display': 'inline-block'}),
    dcc.Dropdown(id='country-picker', options=country_options,
                 value=country_data['Country/Region'].unique()[0])
])

@app.callback(Output('graph1', 'figure'),
              [Input('country-picker', 'value')])
def update_figure(selected_country):
    df = active_country(selected_country)
    df = df[df['confirmed'] > 0]
    x = df.index.values
    cases = df['confirmed']
    active = df['active']

    trace0 = go.Scatter(
        x=x,
        y=active,
        mode='lines',
        name='active cases'
    )

    trace1 = go.Scatter(
        x=x,
        y=cases,
        mode='lines',
        name='confirmed cases'
    )

    traces = [trace0, trace1]

    return {
        'data': traces,
        'layout': go.Layout(
            title=f'Active cases of COVID-19 for {selected_country}',
            xaxis={'title': 'Date'},
            yaxis={'title': 'Population'}

        )
    }

@app.callback(Output('graph2', 'figure'),
              [Input('country-picker', 'value')])
def update_figure(selected_country):
    df = active_country(selected_country)
    df = df[df['confirmed'] > 0]
    df = df.reset_index()

    trace0 = go.Bar(
        x=df['date'],
        y=df['new_cases']
    )

    traces = [trace0]

    return {
        'data': traces,
        'layout': go.Layout(
            title=f'New cases of COVID-19 for {selected_country}',
            xaxis={'title': 'Date'},
            yaxis={'title': 'New Cases'}

        )
    }


if __name__ == '__main__':
    app.run_server()

