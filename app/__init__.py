import os
from app.utils import create_app


app = create_app(os.environ['FLASK_CONF'])
