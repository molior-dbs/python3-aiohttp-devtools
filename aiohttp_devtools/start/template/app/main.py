from pathlib import Path

from aiohttp import web
# {% if template_engine.is_jinja2 %}
import aiohttp_jinja2
from aiohttp_jinja2 import APP_KEY as JINJA2_APP_KEY
import jinja2
# {% endif %}
import trafaret
from trafaret_config import ConfigError, read_and_validate

from .routes import setup_routes

THIS_DIR = Path(__file__).parent
BASE_DIR = THIS_DIR.parent
SETTINGS_FILE = BASE_DIR / 'settings.yml'

SETTINGS_STRUCTURE = trafaret.Dict(
    {
        # {% if database.is_none and example.is_message_board %}
        'message_file':  trafaret.String() >> (lambda f: BASE_DIR / f),
        # {% endif %}
    })


def load_settings():
    settings_file = SETTINGS_FILE.resolve()
    try:
        settings = read_and_validate(str(settings_file), SETTINGS_STRUCTURE)
    except ConfigError as e:
        # ?
        raise
    return settings

# {% if template_engine.is_jinja2 %}


@jinja2.contextfilter
def reverse_url(context, name, **parts):
    """
    jinja2 filter for generating urls,
    see http://aiohttp.readthedocs.io/en/stable/web.html#reverse-url-constructing-using-named-resources

    Usage:
    {%- raw %}

      {{ 'the-view-name'|url }} might become "/path/to/view"

    or with parts and a query

      {{ 'item-details'|url(id=123, query={'active': 'true'}) }} might become "/items/1?active=true
    {%- endraw %}

    see app/templates.index.jinja for usage.

    :param context: see http://jinja.pocoo.org/docs/dev/api/#jinja2.contextfilter
    :param name: the name of the route
    :param parts: url parts to be passed to route.url(), if parts includes "query" it's removed and passed seperately
    :return: url as generated by app.route[<name>].url(parts=parts, query=query)
    """
    app = context['app']

    kwargs = {}
    if 'query' in parts:
        kwargs['query'] = parts.pop('query')
    if parts:
        kwargs['parts'] = parts
    return app.router[name].url(**kwargs)


@jinja2.contextfilter
def static_url(context, static_file_path):
    """
    jinja2 filter for generating urls for static files. NOTE: heed the warning in create_app about "static_root_url"
    as this filter uses app['static_root_url'].

    Usage:

    {%- raw %}
      {{ 'styles.css'|static }} might become "http://mycdn.example.com/styles.css"
    {%- endraw %}

    see app/templates.index.jinja for usage.

    :param context: see http://jinja.pocoo.org/docs/dev/api/#jinja2.contextfilter
    :param static_file_path: path to static file under static route
    :return: roughly just "<static_root_url>/<static_file_path>"
    """
    app = context['app']
    try:
        static_url = app['static_root_url']
    except KeyError:
        raise RuntimeError('app does not define a static root url "static_root_url"')
    return '{}/{}'.format(static_url.rstrip('/'), static_file_path.lstrip('/'))
# {% endif %}


def create_app(loop):
    app = web.Application(loop=loop)
    app['name'] = '{{ name }}'
    app.update(load_settings())
    # {% if template_engine.is_jinja2 %}

    jinja2_loader = jinja2.FileSystemLoader(str(THIS_DIR / 'templates'))
    aiohttp_jinja2.setup(app, loader=jinja2_loader, app_key=JINJA2_APP_KEY)
    app[JINJA2_APP_KEY].filters.update(
        url=reverse_url,
        static=static_url,
    )
    # {% endif %}

    setup_routes(app)
    return app