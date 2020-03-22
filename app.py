import dash
from flask_caching import Cache

external_stylesheets = ['bWLwgP.css']
# external_stylesheets = ['https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
cache = Cache(server, config={
    'CACHE_TYPE': 'redis',
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory',
    'CACHE_THRESHOLD': 200
})
app.config.suppress_callback_exceptions = True
app.css.config.serve_locally = True

