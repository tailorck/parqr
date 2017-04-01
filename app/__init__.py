from flask import Flask
import logging

app = Flask(__name__)

handler = logging.StreamHandler()
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
