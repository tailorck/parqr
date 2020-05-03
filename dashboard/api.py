import os
import requests
import json
import awsgi
from flask import Flask, make_response, render_template, send_from_directory, request, redirect

app = Flask(__name__, static_folder="static",
            template_folder="templates")
api_endpoint = '/{}/'.format(os.environ.get('stage'))


@app.route('/', methods=['GET', 'POST'])
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if "id_token" not in request.cookies:
        print("ID Token not in cookies: {}".format(request.cookies))
        return make_response(redirect("https://login.parqr.io/login?client_id=5hu4nm2spctsmkpe7f82mvdmm0"
                                      "&response_type=code"
                                      "&scope=aws.cognito.signin.user.admin+email+openid+phone+profile"
                                      "&redirect_uri=https://admin.parqr.io/authenticate"))
    headers = {
        "id_token": request.cookies.get("id_token")
    }
    api_result = requests.get('https://aws.parqr.io/prod/courses', headers=headers)
    print(api_result.text)
    course_info = json.loads(api_result.text)
    headers = {"Content-Type": "text/html"}
    return make_response(render_template('parqr.html', course_info=course_info, len=len(course_info)),
                         200, headers)


@app.route("/authenticate", methods=['GET', 'POST'])
def authenticate():
    code = request.args.get("code")
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    body = {
        "grant_type": "authorization_code",
        "client_id": "5hu4nm2spctsmkpe7f82mvdmm0",
        "redirect_uri": "https://admin.parqr.io/authenticate",
        "code": code
    }
    r = requests.post("https://login.parqr.io/oauth2/token", data=body, headers=headers)
    if r.status_code == 200:
        response = json.loads(r.text)
        id_token = response.get("id_token")
        expires_in = response.get("expires_in")
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("id_token", value=id_token, max_age=expires_in)
        return resp
    else:
        return r.text


@app.route('/static/js/<path:path>')
def send_js(path):
    if "id_token" not in request.cookies:
        print("ID Token not in cookies: {}".format(request.cookies))
        return make_response(redirect("https://login.parqr.io/login?client_id=5hu4nm2spctsmkpe7f82mvdmm0"
                                      "&response_type=code"
                                      "&scope=aws.cognito.signin.user.admin+email+openid+phone+profile"
                                      "&redirect_uri=https://admin.parqr.io/authenticate"))
    return send_from_directory('static/js', path)


@app.route('/static/css/<path:path>')
def send_css(path):
    if "id_token" not in request.cookies:
        print("ID Token not in cookies: {}".format(request.cookies))
        return make_response(redirect("https://login.parqr.io/login?client_id=5hu4nm2spctsmkpe7f82mvdmm0"
                                      "&response_type=code"
                                      "&scope=aws.cognito.signin.user.admin+email+openid+phone+profile"
                                      "&redirect_uri=https://admin.parqr.io/authenticate"))
    return send_from_directory('static/css', path)


def lambda_handler(event, context):
    print(os.environ.get('stage'), event, context)
    response = awsgi.response(app, event, context)
    print(response)
    return response
