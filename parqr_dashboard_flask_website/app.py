# import the Flask class from the flask module
import requests
import json
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm 
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy  import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user


# create the application object
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Thisissupposedtobesecret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/yuhaolan/Documents/Programming/project_ra_parqr_website/databaseDB.db'
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
global user

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(80))
    is_admin = db.Column(db.Boolean, default=False)

class RegisterForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])

class DeleteForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])

class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('remember me')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# use decorators to link the function to a url
@app.route('/parqr')
@login_required
def parqr():
 #call APIs
    params={}
    api_result=requests.get('https://aws.parqr.io/prod/courses',params=params)
    return render_template('parqr.html', current_user=current_user, course_info=json.loads(api_result.text), len=len(json.loads(api_result.text)))
    

@app.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    if current_user.is_admin == False:
        return "You have not permission to view this page!"
    form1 = RegisterForm()
    form2 = DeleteForm()
    if request.method == "POST":
        if form1.validate_on_submit():
            hashed_password = generate_password_hash(form1.password.data, method='sha256')
            createdUser = User.query.filter_by(username=form1.username.data).first()
            if createdUser is not None:
                regristeredUsers = [(item.username) for item in User.query.all()] 
                return render_template('user.html', form1=form1, form2=form2, message1="User already exists!", regristeredUsers=regristeredUsers)

            new_user = User(username=form1.username.data, password=hashed_password, is_admin=False)
            db.session.add(new_user)
            db.session.commit()
            usernames = User.query.all()
            regristeredUsers = [(item.username) for item in usernames] 
            return render_template('user.html', form1=form1, form2=form2, message1="New user has been created successfully!", regristeredUsers=regristeredUsers, current_user=current_user)

        if form2.validate_on_submit():
            if form2.username.data == 'admin12345':
                regristeredUsers = [(item.username) for item in User.query.all()] 
                return render_template('user.html', form1=form1, form2=form2, message2="You cannot delete administrator!", regristeredUsers=regristeredUsers, current_user=current_user)

            deletedUser = User.query.filter_by(username=form2.username.data).first()
            #check user is exist
            if deletedUser is None:
                regristeredUsers = [(item.username) for item in User.query.all()] 
                return render_template('user.html', form1=form1, form2=form2, message2="User is not exist!", regristeredUsers=regristeredUsers, current_user=current_user)
            db.session.delete(deletedUser)
            db.session.commit()
            regristeredUsers = [(item.username) for item in User.query.all()] 
            return render_template('user.html', form1=form1, form2=form2, message2="User has been deleted successfully!", regristeredUsers=regristeredUsers, current_user=current_user)
    else:
        regristeredUsers = [(item.username) for item in User.query.all()] 
        return render_template('user.html', form1=form1, form2=form2, message1=None, message2=None, regristeredUsers=regristeredUsers, current_user=current_user)



    usernames = User.query.all()
    regristeredUsers = [(item.username) for item in usernames] 
    return render_template('user.html', form1=form1, form2=form2, regristeredUsers=regristeredUsers, current_user=current_user)

@app.route('/delete', methods=['POST'])
def delete():
    if "deleteUserName" in request.form:
        deletedUserName = request.form['deleteUserName']
        deletedUser = User.query.filter_by(username=deletedUserName).first()
        regristeredUsers = [(item.username) for item in User.query.all()] 
        if deletedUser is None:
            pass
        if deletedUserName == 'admin12345':
            pass
        else:
            db.session.delete(deletedUser)
            db.session.commit()
            regristeredUsers = [(item.username) for item in User.query.all()] 
            return redirect(url_for('user'))



# route for handling the login page logic
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    checkAdmin = User.query.filter_by(username='admin12345').first()
    if checkAdmin is None:
        hashed_password = generate_password_hash('admin12345', method='sha256')
        new_user = User(username='admin12345', password=hashed_password, is_admin=True)
        db.session.add(new_user)
        db.session.commit()
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                #call APIs
                params={}
                api_result=requests.get('https://aws.parqr.io/prod/courses',params=params)
                print(json.loads(api_result.text))
                return render_template('parqr.html', current_user=user, course_info=json.loads(api_result.text), len=len(json.loads(api_result.text)))
            else:
                return render_template('login.html', form=form, message="The password is wrong. Please try again.")
        else:
            return render_template('login.html', form=form, message="User does not exist. Please try again.")

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)