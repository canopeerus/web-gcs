#!/usr/bin/env python3
from flask import Flask,render_template,redirect,session,abort,request,flash
from flask_sqlalchemy import SQLAlchemy
#from models import GCSUser
import os,uuid
from authutils import verify_password,hash_password
from models import db,GCSUser

app = Flask (__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom (24)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
POSTGRES = {
        'user': 'postgres',
        'pw': 'redwingpostgres',
        'db': 'redwingdb',
        'host':'localhost',
}

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://%(user)s:%(pw)s@%(host)s/%(db)s' % POSTGRES
app.config['WTF_CSRF_ENABLED'] = True

db.app = app
db.init_app (app)

db.create_all ()
db.session.commit ()

@app.route ('/')
def homepage ():
    return render_template("index.html")
    
    
# Main GCS Page route, redirects to 'gcslogin' if not logged in
@app.route ("/gcsportal",methods=['GET','POST'])
def gcs_home():
    if not session.get ('gcs_logged_in'):
        return redirect("/gcslogin",code=302)
    else:
        return render_template("gcshome.html")

# GCS Login page route
@app.route ("/gcslogin")
def gcs_login ():
    if not session.get ('gcs_logged_in'):
        return render_template ("gcs_login.html")

# GCS Login form action route, accepts only POST requests
@app.route ("/gcsloginform",methods=['POST'])
def gcs_login_action ():
    usernameval = request.form['username']
    pwval = request.form['password']
    qresult = GCSUser.query.filter_by (username=usernameval).first()
    if qresult is None:
        return render_template ("gcsloginerr.html")
    qpassword = qresult.password
    qsalt = qresult.salt
    if verify_password (qpassword,pwval,qsalt):
        session['gcs_logged_in'] = True
        session['gcs_user'] = usernameval
        return redirect("/gcsportal",code=302)
    else:
        return render_template ("gcsloginerr.html")

# show user profile and account settings
@app.route ("/gcsuserprofile",methods=['POST','GET'])
def show_userprofile():
    if 'gcs_logged_in' in session:
        if session['gcs_logged_in']:
            user = session['gcs_user']
            qresult = GCSUser.query.filter_by(username=user).first()
            return render_template ("gcsprofile.html",username = qresult.username, firstname = qresult.firstname, lastname = qresult.lastname,email_id = qresult.email_id)

    else:
        return redirect ("/gcslogin",code=302)

# Log out route
@app.route ("/gcslogout",methods=['POST'])
def gcs_logout():
    if session ['gcs_logged_in']:
        del session['gcs_user']
        session['gcs_logged_in'] = False;
    return redirect ("/", code=302)

# GCS Sign up page route
@app.route ("/gcssignup")
def gcs_signup ():
    return render_template ("gcs_signup.html")

# GCS Sign up page form action route
@app.route ("/gcssignupform",methods=['POST'])
def gcs_signup_action ():
    salt = uuid.uuid4().hex
    pwd_hash = hash_password (request.form['password'],salt)
    match = GCSUser.query.filter_by (username = request.form['username']).first()
    if match is None:
        gcsuser_instance = GCSUser (username = request.form['username'],password = pwd_hash,
            salt = salt, firstname = request.form['firstname'], lastname = request.form['lastname'], 
            email_id = request.form['email_id'])
        db.session.add (gcsuser_instance)
        db.session.commit ()
        return redirect ("/gcslogin",code=302)
    else:
        return render_template ("gcs_signup_err.html")


@app.route ("/gcsprofileedit",methods=['POST'])
def gcs_profile_edit ():
    if 'gcs_user' not in session:
        return redirect ("/gcslogin",code=302)
    user = session['gcs_user']
    user_instance = GCSUser.query.filter_by (username = user).first()
    if 'firstname' in request.args:
        n_fname = request.args['firstname']
        user_instance.firstname = n_fname
    if 'lastname' in request.args:
        n_lname = request.args['lastname']
        user_instance.lastname = n_lname
    if 'email' in request.args:
        n_email = request.args['email']
        user_instance.email_id = n_email
    db.session.commit()
    return redirect ("/gcsuserprofile",code=302)

if __name__ == "__main__":
    app.run (debug = True)
