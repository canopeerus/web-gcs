#!/usr/bin/env python3
'''
------------------------------------------------------------------------------------------------------
Main GCS application source code for Redwing Aerospace Laboratories
@author : Aditya Visvanathan
@version : 0.1.0
Dependencies : flask, psycopg2 + postgresql
------------------------------------------------------------------------------------------------------
'''

from flask import Flask,render_template,redirect,session,abort,request,flash,url_for,send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os,uuid,visualise,shutil,time
from authutils import verify_password,hash_password
from models import db,GCSUser,Drone,Job,Payload

UPLOADS_FOLDER = '/var/www/html/web-gcs/uploads/'
ALLOWED_LOGS_EXTENSIONS = set (['csv'])

app = Flask (__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = b'\xad]\xb8\xcf\x85\xe0\x0cp\xecf\x8ez\x86\x9d\x16%\xa5F\x08\x9c\xb6\x11\xc2\x86'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

if os.environ['ENV'] == 'prod':
    app.config['UPLOAD_FOLDER'] = "uploads/"
else:
    app.config['UPLOAD_FOLDER'] = UPLOADS_FOLDER

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

'''
---------------------------------------------------
IMAGE UPLOAD LOADING FOR PLOTS AND VISUALIZATIONS
---------------------------------------------------
'''
@app.route ('/image/<path:filename>')
def download_file (filename):
	return send_from_directory (app.config["UPLOAD_FOLDER"],filename, as_attachment=True)

def allowed_file (filename):
    return '.' in filename and \
            filename.rsplit ('.',1)[1].lower() in ALLOWED_LOGS_EXTENSIONS

@app.route ('/')
def homepage ():
    return render_template("index.html")
    
  
'''
---------------------------------
LANDING PAGE
---------------------------------
'''
# Main GCS Page route, redirects to 'gcslogin' if not logged in
@app.route ("/gcsportal",methods=['GET','POST'])
def gcs_home():
    if 'gcs_user' in session and session['gcs_logged_in']:
        return render_template ('gcshome.html')
    else:
        return redirect ('/gcslogin',code = 302)

'''
----------------------------------
GCS USER PROFILE ACTIONS
----------------------------------
'''
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
        return render_template ("gcs_login.html",result="error")
    qpassword = qresult.password
    qsalt = qresult.salt
    if verify_password (qpassword,pwval,qsalt):
        session['gcs_logged_in'] = True
        session['gcs_user'] = usernameval
        session.modified = True
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


'''
-------------------------------
DRONE ACTION ROUTES
-------------------------------
'''
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

# New drone input form action route
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


# View particular drone
@app.route ("/droneview")
def individual_drone ():
    if 'gcs_user' in session:
        if 'drone' not in request.args:
            return "<h2>The given request was not understood correctly</h2>"
        r_drone_name = request.args.get('drone')
        drone_instance = Drone.query.filter_by (drone_name = r_drone_name).first()
        return drone_instance.drone_name + drone_instance.model

    else:
        return redirect ('/gcslogin',code = 302)


'''
--------------------------------
INVENTORY
--------------------------------
'''
# Inventory
@app.route ('/inventory')
def main_inventory (methods=['GET']):
    if 'gcs_user' in session and session['gcs_logged_in']:
        payloads = Payload.query.all ()
        payloads_list = []
        for p in payloads:
            payloads_list.append ([p.id,p.name,p.weight])
        count = len (payloads_list)
        return render_template ("inventory.html",inventory = payloads_list,count = count)
    else:
        return redirect ('/gcslogin',code = 302)


'''
-----------------------------------
MAP
-----------------------------------
'''
# Map action
@app.route ('/map')
def show_map ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        return render_template ('maps.html')
    else:
        return redirect ('/gcslogin',code=302)


'''
------------------------------------------
LOG FILE VISUALIZATION
------------------------------------------
'''
# Visualisations/plot from arjun
@app.route ('/logplotter')
def visualize_logs_input ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        return render_template ('visualize_input.html',parameters = visualise.params_list)
    else:
        return redirect ('/gcslogin',code = 302)

@app.route ('/visualizefile',methods=['GET','POST'])
def visualize_logs ():
    if request.method == 'POST':
        if 'gcs_user' in session and session['gcs_logged_in']:
            if not 'file' in request.files:
                return 'error:no file'
            inputfile = request.files.get ('file')
            if allowed_file (inputfile.filename):
                filename = inputfile.filename
                s_param = request.form.get ('para_select')
                outpath = os.path.join (app.config['UPLOAD_FOLDER'],filename)
                imgpath = os.path.join (app.config['UPLOAD_FOLDER'],'plot.png')
                inputfile.save (outpath)
                ret_val = visualise.rvisualize (outpath,imgpath,param = s_param)
                if ret_val == 0:
                    os.remove (outpath)
                    image = 'plot.png'
                    return render_template ('visualize_input.html',
                            image = image,parameters = visualise.params_list)
            else:
                return "Invalid file format"
        else:
            return redirect ('/gcslogin',code = 302)
        return "done"
    else:
        return redirect ('/gcsportal',code = 302)


'''
---------------------------------------
JOBS/DEPLOYMENT RELATED ACTIONS
---------------------------------------
'''
# Deployment/job tracker
@app.route ("/jobtracker")
def show_jobs ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        jobs = Job.query.all()
        jobslist = []
        for job in jobs:
            jobslist.append ([job.date,job.location_dest_string,job.status])
        count = len(jobs)
        return render_template ("jobs.html", deployments = jobslist, length = count)
    else:
        return redirect ('/gcslogin',code = 302)
            
# Form page for adding new job
@app.route ("/newdeployment")
def new_job ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        drones = Drone.query.all()
        droneslist = []
        for x in drones:
            droneslist.append ([x.drone_name,x.id])

        return render_template ('newjob.html',drones = droneslist)
    else:
        return redirect ('/gcslogin',code = 302)

@app.route ('/newjobform',methods=['POST'])
def new_job_formaction ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        date_sel = request.form.get ('date')
        time_sel = request.form.get ('time')
        datetime_sel = datetime.strptime (date_sel + ' ' + time_sel, '%Y-%m-%d %I:%M %p')
        drone_id = int(str (request.form.get ('drone_select')))
        location_origin_lat_sel = request.form.get ('origin-lat')
        location_origin_lon_sel = request.form.get ('origin-lon')
        location_dest_lat_sel = request.form.get ('dest-lat')
        location_dest_lon_sel = request.form.get ('dest-lon')
        job_instance = Job (date_sel,drone_id,location_origin_lat_sel,
                location_origin_lon_sel,location_dest_lat_sel,location_dest_lon_sel,1)
        return "Deployment input detected! Database in progress(payloads unavailable)"
        '''
        db.session.add (job_instance)
        db.session.commit()
        return redirect ('/jobtracker',code = 302)
        '''
    else:
        return redirect ('/gcslogin',code = 302)


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
