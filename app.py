#!/usr/bin/env python3
from flask import Flask,render_template,redirect,session,abort,request,flash
from flask_sqlalchemy import SQLAlchemy
#from models import GCSUser
import os

app = Flask (__name__)
app.config['DEBUG'] = True
POSTGRES = {
        'user': 'postgres',
        'pw': 'redwingpostgres',
        'db': 'redwingdb',
        'host':'localhost',
}

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://%(user)s:%(pw)s@%(host)s/%(db)s' % POSTGRES
app.config['WTF_CSRF_ENABLED'] = True

db = SQLAlchemy (app)


class GCSUser (db.Model):
    __tablename__ = 'gcsusers'
    id = db.Column (db.Integer, primary_key = True)
    username = db.Column (db.String(),unique = True)
    password = db.Column (db.String(),unique = True)

    def __init__ (self, username, password):
        self.username = username
        self.password = password

    def __repr__ (self):
        return '<id {}>'.format (self.id)

    def serialize (self):
        return {
                'id':self.id,
                'username':self.username,
                'password':self.password
                }
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
    session['gcs_logged_in'] = True
    return redirect("/gcsportal",code=302)

# GCS Sign up page route
@app.route ("/gcssignup")
def gcs_signup ():
    return render_template ("gcs_signup.html")

# GCS Sign up page form action route
@app.route ("/gcssignupform",methods=['POST'])
def gcs_signup_action ():
    gcsuser_instance = GCSUser (username = request.form['username'],password = request.form['password'])
    db.session.add (gcsuser_instance)
    db.session.commit ()
    return "Registered"

if __name__ == "__main__":
    app.run (debug = True)
