import requests
from flask_restful import Resource
from flask import render_template

class Dashboard(Resource):
    def _init_(self):
        pass
    def get(self):
        params={}
        api_result=requests.get('https://aws.parqr.io/prod/courses',params=params)
        return render_template('parqr.html', course_info=json.loads(api_result.text), len=len(json.loads(api_result.text)))

