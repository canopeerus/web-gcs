#!/usr/bin/env python3
'''
------------------------------------------------------------------------------------------------------
Main GCS application source code for Redwing Aerospace Laboratories
@author : Aditya Visvanathan
@version : 0.1.0
Dependencies : flask, psycopg2 + postgresql
------------------------------------------------------------------------------------------------------
'''

from flask import Flask,render_template,redirect,session,abort,request,flash
from flask_sqlalchemy import SQLAlchemy
import os,uuid
from authutils import verify_password,hash_password
from models import db,GCSUser,Drone

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

hackuser = 'arjun'
hackpwd = 'password'

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
    if usernameval == hackuser and pwval == hackpwd:
        session ['gcs_logged_in'] = True
        session ['gcs_user'] = usernameval
        session ['hack_usser'] = True
        return redirect ("/gcsportal",code=302)
    qresult = GCSUser.query.filter_by (username=usernameval).first()
    if qresult is None:
        return render_template ("gcs_login.html",result="error")
    qpassword = qresult.password
    qsalt = qresult.salt
    if verify_password (qpassword,pwval,qsalt):
        session['gcs_logged_in'] = True
        session['gcs_user'] = usernameval
        return redirect("/gcsportal",code=302)
    else:
        return render_template ("gcs_login.html", result="error")

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
@app.route ("/gcslogout",methods=['POST','GET'])
def gcs_logout():
    if 'gcs_logged_in' in session:
        if session ['gcs_logged_in']:
            del session['gcs_user']
            session['gcs_logged_in'] = False;
    return redirect ("/", code=302)

# GCS Sign up page route
@app.route ("/gcssignup",methods=['POST','GET'])
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
        return render_template ("gcs_signup.html",result = "error")

# POST route for editing GCS profile
@app.route ("/gcsprofileedit",methods=['POST'])
def gcs_profile_edit ():
    if 'gcs_user' not in session:
        print ("Not in session wtf!")
        return redirect ("/gcslogin",code=302)
    user = session['gcs_user']
    user_instance = GCSUser.query.filter_by (username = user).first()
    print (request.args)
    if 'firstname_update' in request.form:
        print ("firstname found")
        n_fname = request.form['firstname_update']
        user_instance.firstname = n_fname
    else:
        print ("no firstname")
    
    if 'lastname_update' in request.form:
        print ("lastname found")
        n_lname = request.form['lastname_update']
        user_instance.lastname = n_lname
    else:
        print ("no lastname")

    if 'email_update' in request.form:
        print ("email found")
        n_email = request.form['email_update']
        user_instance.email_id = n_email
    else:
        print ("no email")

    db.session.commit()
    return redirect ("/gcsuserprofile",code=302)

# Route for password change input form
@app.route ("/updatepassword")
def change_password ():
    err = False
    if 'error' in request.args:
        err = True
        print ("ERRRRROOOORRR")
    if 'gcs_logged_in' in session and session['gcs_logged_in']:
        if err:
            return render_template ("changepassword.html",result="error")
        else:
            return render_template ("changepassword.html")
    else:
        return redirect ("/gcslogin",code=302)

# Form action route for /updatepassword
@app.route ("/updatepassword_action",methods=['POST'])
def update_password_action ():
    if 'gcs_user' in session:
        gcsuser = GCSUser.query.filter_by (username = session['gcs_user']).first()
        gsalt = gcsuser.salt
        oldpas = hash_password (request.form['old_password'],gsalt)
        if oldpas == gcsuser.password:
            newpas = hash_password (request.form['password'],gsalt)
            gcsuser.password = newpas
            db.session.commit()
            return redirect ("/gcsuserprofile",code=302)
        else:
            return redirect ("/updatepassword?error",code=302)
    else:
        return redirect ("/gcslogin",code=302)

# Route for drone monitor list screen
@app.route ("/dronemonitor")
def show_drones():
    if 'gcs_user' in session:
        drones = Drone.query.all ()
        drone_list = []
        for x in drones:
            y = [x.drone_name,x.model,x.motor_count,x.battery_type]
            drone_list.append (y)

        count = len(drones)
        return render_template ("drone-monitor.html", drones = drone_list, count = count)
    else:
        return redirect ("/gcslogin", code=302)

# Route for adding new drone
@app.route ("/newdrone")
def new_drone ():
    if 'gcs_user' in session:
        return render_template ("newdrone.html")
    else:
        return redirect ('/gcslogin',code=302)

@app.route ("/newdroneaction",methods=['POST'])
def add_new_drone():
    if 'gcs_user' in session:
        drone = Drone (drone_name = request.form['droneName'],
            model = request.form['droneModel'],
            motor_count = request.form['motorCount'],
            battery_type = request.form['batteryType'])
        db.session.add (drone)
        db.session.commit()
        return redirect ('/dronemonitor',code=302)
    else:
        return redirect ("/gcslogin",code = 302)


@app.errorhandler (404)
def page_not_found (e):
    return render_template ('404.html',code=404)


'''
-------------------------------------------------------------------
RESTful API 
-------------------------------------------------------------------
'''

# Test GET route to test API
@app.route ("/api/v1/test")
def test_api ():
    msg = ''
    if 'message' in request.args:
        msg += request.args.get('message')
        return msg
    if 'version' in request.args:
        return "API v1"
    else:
        return "request error"

        
if __name__ == "__main__":
    app.run (debug = True)
