import os
from utils import create_app

app = create_app(os.environ['FLASK_CONF'])
