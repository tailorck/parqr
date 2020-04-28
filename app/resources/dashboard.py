import requests
import json
from flask_restful import Resource
from flask import render_template

class Dashboard(Resource):
    
    def _init_(self):
        pass

    def get(self):
        api_result=requests.get('https://aws.parqr.io/dev/courses')
        course_info=json.loads(api_result.text)
        return render_template('parqr.html', course_info=course_info, len=len(course_info))