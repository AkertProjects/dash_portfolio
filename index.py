import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import logging

from app import app
from apps import coronavirus

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

server = app.server

# add other pages here, I just linked them to the same thing due
# to lazyness
index_page = html.Div([
    dcc.Link('Coronavirus Dash', href='/coronavirus'),
    html.Br()
])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    # add other paths here
    if pathname == '/coronavirus':
        return coronavirus.layout.layout()
    else:
        return index_page

if __name__ == '__main__':
    # debug=True, wil cause it to run twice... weird/annoying behavior
    app.run_server(host="0.0.0.0", port=8050, debug=True)

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)