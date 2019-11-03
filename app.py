#!/usr/bin/env python3
'''
------------------------------------------------------------------------------------------------------
Main GCS application source code for Redwing Aerospace Laboratories
@author : Aditya Visvanathan
@version : 0.1.0
Dependencies : flask, psycopg2 + postgresql,geocoer,flask_sqlalchemy
------------------------------------------------------------------------------------------------------
'''

from collections import Counter
from flask import Flask,render_template,redirect,session,abort,request,flash,url_for,send_from_directory,send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os,uuid,visualise,shutil,time,geocoder
from authutils import verify_password,hash_password
from models import db,GCSUser,Drone,Job,Payload,Incident,LogFile
from flask_pymongo import PyMongo
import pandas as pd

DOC_FOLDER = '/var/www/html/web-gcs/docs/build/'
UPLOADS_FOLDER = '/var/www/html/web-gcs/uploads/'
ALLOWED_LOGS_EXTENSIONS = set (['csv'])
ALLOWED_BATCH_INVENTORY_TYPES  = ALLOWED_LOGS_EXTENSIONS

status_list = ['Pending Action','Resolved']
priority_list = ['Low','Medium','High']

app = Flask (__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = b'\xad]\xb8\xcf\x85\xe0\x0cp\xecf\x8ez\x86\x9d\x16%\xa5F\x08\x9c\xb6\x11\xc2\x86'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

if os.environ.get('ENV') == 'prod':
    app.config['UPLOAD_FOLDER'] = "uploads/"
    app.config['DOC_FOLDER'] = "docs/build/"
else:
    app.config['UPLOAD_FOLDER'] = UPLOADS_FOLDER
    app.config["DOC_FOLDER"] = DOC_FOLDER

POSTGRES = {
        'user': 'postgres',
        'pw': 'redwingpostgres',
        'db': 'redwingdb',
        'host':'localhost',
}

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://%(user)s:%(pw)s@%(host)s/%(db)s' % POSTGRES
app.config['WTF_CSRF_ENABLED'] = True
app.config ['MONGO_URI'] = 'mongodb://localhost:27017/redwingdb'
app.config ["ACCEPTABLE_COLUMNS"] = ['type','item','storage_type','item_type','weight',
        'uom','stock','value']

db.app = app
db.init_app (app)

mongo = PyMongo (app)
mongo.init_app (app)

logfile_collection = mongo.db.logfiles

db.create_all ()
db.session.commit ()


'''
---------------------------------------------------
IMAGE UPLOAD LOADING FOR PLOTS AND VISUALIZATIONS
---------------------------------------------------
'''
@app.route ('/image/<path:filename>')
def download_file (filename):
	return send_from_directory (app.config["UPLOAD_FOLDER"],filename)

def allowed_file (filename):
    return '.' in filename and \
            filename.rsplit ('.',1)[1].lower() in ALLOWED_LOGS_EXTENSIONS



'''
---------------------------------------------
LANDING PAGE
---------------------------------------------
'''
@app.route ('/')
def homepage ():
    return render_template("index.html")
    
  
# Main GCS Page route, redirects to 'gcslogin' if not logged in
@app.route ("/gcsportal",methods=['GET','POST'])
def gcs_home():
    if 'gcs_user' in session and session['gcs_logged_in']:
        return redirect ('/jobtracker',code = 302)
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
        return render_template ("fmsgeneric/gcs_login.html")

# GCS Login form action route, accepts only POST requests
@app.route ("/gcsloginform",methods=['POST'])
def gcs_login_action ():
    usernameval = request.form['username']
    pwval = request.form['password']
    qresult = GCSUser.query.filter_by (username=usernameval).first()
    if qresult is None:
        return render_template ("fmsgeneric/gcs_login.html",result="error")
    qpassword = qresult.password
    qsalt = qresult.salt
    if verify_password (qpassword,pwval,qsalt):
        session['gcs_logged_in'] = True
        session['gcs_user'] = usernameval
        session.modified = True
        return redirect("/gcsportal",code=302)
    else:
        return render_template ("fmsgeneric/gcs_login.html", result="error")

# show user profile and account settings
@app.route ("/gcsuserprofile",methods=['POST','GET'])
def show_userprofile():
    if 'gcs_user' in session and session['gcs_logged_in']:
        updated = 0
        if 'updated' in request.args:
            updated = 1
        user = session['gcs_user']
        qresult = GCSUser.query.filter_by(username=user).first()
        return render_template ("fmsgeneric/gcsprofile.html",
                username = qresult.username, firstname = qresult.firstname,
                lastname = qresult.lastname,email_id = qresult.email_id,
                updated = updated)

    else:
        return redirect ("/gcslogin",code=302)

# Log out route
@app.route ("/gcslogout",methods=['POST','GET'])
def gcs_logout ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        del session['gcs_user']
        session['gcs_logged_in'] = False
    return redirect ("/", code=302)

# GCS Sign up page route
@app.route ("/gcssignup",methods=['POST','GET'])
def gcs_signup ():
    return render_template ("fmsgeneric/gcs_signup.html")

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
        return render_template ("fmsgeneric/gcs_signup.html",result = "error")

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
    return redirect ("/gcsuserprofile?updated",code=302)

# Route for password change input form
@app.route ("/updatepassword")
def change_password ():
    err = False
    if 'error' in request.args:
        err = True
        print ("ERRRRROOOORRR")
    if 'gcs_logged_in' in session and session['gcs_logged_in']:
        if err:
            return render_template ("fmsgeneric/changepassword.html",result="error")
        else:
            return render_template ("fmsgeneric/changepassword.html")
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
        count = len(drones)
        return render_template ("drone/index.html", drones = drones, count = count)
    else:
        return redirect ("/gcslogin", code=302)

# Route for adding new drone
@app.route ("/newdrone")
def new_drone ():
    if 'gcs_user' in session:
        return render_template ("drone/newdrone.html")
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
    if 'gcs_user' in session and session['gcs_logged_in']:
        
        if 'drone' not in request.args:
            return "<h2>The given request was not understood correctly</h2>"
       
        drone_arg = request.args.get ('drone')
        if drone_arg == 'undefined' or drone_arg is None:
            return "<h2> The given request was not understood correctly</h2>"
        
        r_drone_id = int (drone_arg)
        drone_instance = Drone.query.filter_by (id = int(r_drone_id)).first()
        if drone_instance is None:
            return "<h2 style='text-align:center;'>Unable to process this request</h2>"
        jobslist = []
        
        if drone_instance.has_jobs_scheduled ():
            id_array = drone_instance.job_queue_int ()
            print (id_array)
            for iden in id_array:
                job = Job.query.filter_by (id = iden).first()
                jobslist.append (job)
        
        count = len(jobslist)
        
        if 'error' in request.args:
            strerr = 'deleteerror'
        else:
            strerr = 'noerror'
        return render_template ("drone/droneview.html",drone = drone_instance,jobs = jobslist,count = count,error = strerr)
    else:
        return redirect ('/gcslogin',code = 302)

# Disable drone
@app.route ("/disabledrone")
def terminate_drone ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        
        if 'drone' not in request.args:
            return "<h2>The given request was not understood correctly</h2>"
        r_drone_id = int(request.args.get ('drone'))
        drone = Drone.query.filter_by (id = r_drone_id).first ()
        if drone.disable ():
            return redirect ('/dronemonitor',code = 302)
        else:
            return redirect ('/droneview?error&drone='
                    +str(r_drone_id),code = 302)
    else:
        return redirect ('/gcslogin',code = 302)



'''
---------------------------------------
LOG FILE STORAGE DATABASE
---------------------------------------
'''
@app.route ('/logfilestorage')
def logfilestorage ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        files = LogFile.query.all ()
        length = len(files)
        return render_template ('LogStorage/index.html',files = files,length = length)

    else:
        return redirect ('/gcslogin',code = 302)

@app.route ('/newlogupload')
def newfile ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        drones = Drone.query.all ()
        return render_template ('LogStorage/newfile.html',drones = drones)
    else:
        return redirect ('/gcslogin',code = 302)

@app.route ('/newfileaction',methods=['POST'])
def newfileaction ():
    if request.method == 'POST':
        if 'gcs_user' in session and session ['gcs_logged_in']:
            if not 'file' in request.files:
                return 'error:no file'
            inputfile = request.files.get ('file')
            drone_id = int(request.form.get ('drone_select'))
            drone_name = Drone.query.filter_by (id = drone_id).first ().drone_name
            if drone_name is None:
                return "error!!!!"
            
            if allowed_file (inputfile.filename):
                username = session ['gcs_user']
                user_id = GCSUser.query.filter_by (username = username).first ().id

                blob = inputfile.read ()
                fsize = len (blob)
                log_instance = LogFile (inputfile.filename,user_id,username,
                        drone_id,drone_name,fsize)
                

                mongo.save_file (inputfile.filename,inputfile,base = 'logfiles')
                db.session.add (log_instance)
                db.session.commit ()

                return redirect ('/logfilestorage',code = 302)
                
            else:
                return "Invalid file format"
        else:
            return redirect ('/gcslogin',code = 302)
        return "done"
    else:
        return redirect ('/gcsportal',code = 302)

@app.route ('/file/<filename>')
def file (filename):
    return mongo.send_file (filename,base = 'logfiles')

@app.route ('/logdownload')
def download_logfile ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        if 'id' not in request.args:
            return "ERROR"
        fileId = int (request.args.get ('id'))
        file_instance = LogFile.query.filter_by (id = fileId).first ()
        fname = file_instance.filename
        return redirect ('/file/'+fname,code = 302)
    else:
        return redirect ('/gcslogin',code = 302)



'''
--------------------------------
INVENTORY
--------------------------------
'''
# Inventory
@app.route ('/inventory')
def main_inventory ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        payloads = Payload.query.all ()
        count = len (payloads)
        return render_template ("inventory/index.html",inventory = payloads,count = count)
    else:
        return redirect ('/gcslogin',code = 302)

#@app.route ('/inventoryitem')
#def edit_inventory_item (methods=['GET']):

@app.route ('/addinventory')
def new_inventory ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        payloads = Payload.query.all ()
        types = []
        storage_types = []
        items = []
        uoms = []
        for p in payloads:
            if p.type_str in types:
                types.append (p.type_str)
            if p.storage_type in storage_types:
                storage_types.append (p.storage_type)
            if p.item in items:
                items.append (p.item)
            if p.uom in uoms:
                uoms.append (p.uom)
        return render_template ('inventory/newinventory.html',types = types,items = items,
                storage_types = storage_types,uoms = uoms)
    else:
        return redirect ('/gcslogin',code = 302)


@app.route ('/newinventoryaction',methods=['POST'])
def inventoryformaction ():
    if request.method == 'POST':
        if 'gcs_user' in session and session ['gcs_logged_in']:
            type_sel = request.form ['type_select']
            if type_sel == 'New Type':
                type_str = request.form ['newitemType']
            else:
                type_str = type_sel

            item_sel = request.form ['item_select']
            if item_sel == 'New Item':
                item = request.form['item']
            else:
                item = item_sel

            storage_sel = request.form ['storage_type_select']
            if storage_sel == 'New Storage Type':
                storage_type = request.form['storageType']
            else:
                storage_type = storage_sel

            item_type = request.form['itemType']
            item_weight = request.form['weight']
            
            uom_sel = request.form ['uom_select']
            if uom_sel == 'new_uom':
                uom = request.form['newUom']
            else:
                uom = uom_sel

            stock = request.form ['stock']

            value = request.form['value']

            payload = Payload (type_str,item,storage_type,item_type,item_weight,uom,
                    stock,value)

            db.session.add (payload)
            db.session.commit ()
            return redirect ('/inventory',code = 302)
        else:
            return redirect ('/gcslogin',code = 302)
    else:
        return redirect ('/gcsportal',code = 302)
   
@app.route ('/batchinventoryupload',methods=['GET'])
def batchupload_page ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        return render_template ('inventory/batchinventory_upload.html')
    else:
        return redirect ('/gcslogin',code = 302)


def csv_allowed_file (filename):
    return '.' in filename and  \
            filename.rsplit ('.',1)[1].lower() in ALLOWED_BATCH_INVENTORY_TYPES

@app.route ('/batchinventoryaction',methods=['POST'])
def batchinventory_action ():
    if request.method == 'POST':
        if 'gcs_user' in session and session ['gcs_logged_in']:
            if not 'file' in request.files:
                return 'error:no file'
            inputfile = request.files.get ('file')
            if inputfile is None:
                return "The fuck"
            if csv_allowed_file (inputfile.filename):
                filename = inputfile.filename
                outpath = os.path.join (app.config['UPLOAD_FOLDER'],filename)
                inputfile.save (outpath)
                df = pd.read_table (outpath,sep=',')
                read_columns = list (df.columns.values)
                if Counter (read_columns) == Counter (app.config['ACCEPTABLE_COLUMNS']):
                    for index,row in df.iterrows():
                        inventory_item = Payload (row['type'],row['item'],row['storage_type'],
                            row['item_type'],int(row['weight']),row['uom'],
                            int(row['stock']),float(row['value']))
                        db.session.add (inventory_item)
                
                    db.session.commit ()
                    os.remove (outpath)
                else:
                    return "The uploaded csv file is of invalid format"
                return redirect ('/inventory',code = 302)
            else:
                return "Invalid file format"
        else:
            return redirect ('/gcslogin',code = 302)
    else:
        return "ERROR"



@app.route ('/inventoryitem',methods=['GET'])
def inventoryitemdisplay ():
    return "<h1 style='text-align:center;'>Inventory edit is being worked on. Unavailable at the moment</h1>"
    '''
    if 'gcs_user' in session and session['gcs_logged_in']:
        if 'item' in request.args:
            itemId = request.args['item']
            itemId = int (itemId)
            payload = Payload.query.filter_by (id = itemId).first ()
            if payload is None:
                return "Item not Found"
            else:
                return render_template ('editinventory.html',name = payload.name,
                    weight = payload.weight,stock = payload.stock)
        else:
            return redirect ('/gcsportal',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)
    '''

'''
-----------------------------------
MAP
-----------------------------------
'''
# Map action
@app.route ('/map')
def show_map ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        jobslist = Job.query.all ()
        return render_template ('maps.html',jobs = jobslist)
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


@app.route ('/logfileupload')
def log_file_storage ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        drones = Drone.query.all ()
        count = len(drones)
        return render_template ('logfilestorage.html',drones = drones,count = count)
    else:
        return redirect ('/gcslogin',code = 302)

'''
--------------------------------------
NPNT AUTHENTICATION
--------------------------------------
'''
# NPNT tool page
@app.route ('/npntauthentication')
def npntauthroute ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        return render_template ('npntpage.html')
    else:
        return redirect ('/gcslogin',code = 302)


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
        count = len(jobs)
        return render_template ("jobs/jobs.html", deployments = jobs, length = count)
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
        payloads = Payload.query.all ()
        return render_template ('jobs/newjob.html',drones = drones,payloads = payloads)
    else:
        return redirect ('/gcslogin',code = 302)

# Form action route for adding new job/deployment
@app.route ('/newjobform',methods=['POST'])
def new_job_formaction ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        date_sel = request.form.get ('date')
        time_sel = request.form.get ('time')
        datetime_sel = datetime.strptime (date_sel + ' ' + time_sel, '%Y-%m-%d %I:%M %p')
        drone_id = int(str (request.form.get ('drone_select')))
        location_origin_lat_sel = request.form.get ('origin-lat')
        location_origin_lon_sel = request.form.get ('origin-long')
        location_dest_lat_sel = request.form.get ('dest-lat')
        location_dest_lon_sel = request.form.get ('dest-long')
        payload_id = request.form.get ('payload_select')
        latlng = [float (location_dest_lat_sel),float (location_dest_lon_sel)]
        count = int (request.form.get ('count'))
        
        g = geocoder.mapbox (latlng,method='reverse',key='pk.eyJ1IjoiY2Fub3BlZXJ1cyIsImEiOiJjandidGhuZDkwa2V2NDl0bDhvem0zcDMzIn0.g1NXF5VQiDwn66KAsr-_dw')
        if g.json is None:
            location_str_dest = "Unknown Location"
        else:
            location_str_dest = g.json['address']
        
        latlng = [float (location_origin_lat_sel),float(location_origin_lon_sel)]
        g = geocoder.mapbox (latlng,method='reverse',key='pk.eyJ1IjoiY2Fub3BlZXJ1cyIsImEiOiJjandidGhuZDkwa2V2NDl0bDhvem0zcDMzIn0.g1NXF5VQiDwn66KAsr-_dw')
        if g.json is None:
            location_str_origin = "Unknown Location"
        else:
            location_str_origin = g.json['address']
        
        job_instance = Job (datetime_sel,drone_id,location_origin_lat_sel,
                location_origin_lon_sel,location_dest_lat_sel,location_dest_lon_sel,
                location_str_dest,int (payload_id),count,location_str_origin)

        db.session.add (job_instance)
        db.session.commit ()

        drone_sel = Drone.query.filter_by(id = drone_id).first ()
        drone_sel.assign_job (job_instance.id)
        db.session.commit ()
       
        return redirect ('/jobtracker',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)


# Form action for filters for job search
@app.route ('/filterjobs',methods=['POST'])
def filterjobs ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        begindatetimestr = request.form.get ('begindate') + ' ' + request.form.get ('begintime')
        begindatetime = datetime.strptime (begindatetimestr, '%Y-%m-%d %I:%M %p')

        endstr = request.form.get ('enddate') + ' ' + request.form.get ('endtime')
        enddatetime = datetime.strptime (endstr,'%Y-%m-%d %I:%M %p')


        jobmatch = Job.query.filter (Job.date < enddatetime,Job.date >= begindatetime).all()
        if jobmatch is not None:
            return render_template ('jobs/jobs.html',deployments = jobmatch)
        else:
            return render_template ('jobs/jobs.html',error = 'matcherror')
    else:
        return redirect ('/gcslogin',code = 302)

# particular Job details view
@app.route ('/jobview')
def jobview ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        if 'job' in request.args:
            jobid_str = request.args.get ('job')
            if jobid_str == 'undefined' or jobid_str is None:
                return "<h2 style='text-align:center;'>The request was not understood</h2>"
            else:
                jobid = int (jobid_str)
                job_instance = Job.query.filter_by (id = jobid).first ()
                if job_instance is not None:
                    if job_instance.is_pending ():
                        return render_template ('jobview.html',jobid = job_instance.id)
                    else:
                        return "<h2>Work In Progress</h2>"
                else:
                    return redirect ('/jobtracker',code = 302)
        else:
            return "<h2 style='text-align:center;'>ERROR,Something went wrong</h2>"
    else:
        return redirect ('/gcslogin',code = 302)

# OTP form action route
@app.route ('/jobotpauth',methods=['POST'])
def auth_otp ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        if 'otp' in request.form and 'jobid' in request.form:
            onetime_password = request.form.get ('otp')
            jobid = request.form.get ('jobid')
            if onetime_password == '0000':
                return redirect ('/godeployment?job='+jobid,code = 307)
            else:
                return render_template ('jobs/jobotp.html',errorstr = "matcherror")
        else:
            return render_template ('jobs/jobotp.html',errorstr = 'generror')
    else:
        return redirect ('/gcslogin',code = 302)


# Deployment initiate path
@app.route ('/initiatedeployment',methods=['POST'])
def initiate_deployment ():
    if request.method == 'POST':
        if 'gcs_user' in session and session['gcs_logged_in']:
            jobid = int(request.args.get ('job'))
            job_instance = Job.query.filter_by (id = jobid).first ()
            if job_instance is not None:
                drone_instance = Drone.query.filter_by (id = job_instance.id).first()
                payload_instance = Payload.query.filter_by (id = job_instance.payload_id).first()
                return render_template ('jobs/jobview.html',job = job_instance,
                        drone = drone_instance, payload = payload_instance)
            else:
                return "<h3> Something went wrong</h3>"
        else:
            return redirect ('/gcslogin',code = 302)
    else:
        return "<h2>Error,Only post requests allowed!</h2>"


@app.route ('/godeployment')
def go_deployment ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        jobid = int (request.args.get ('job'))
        job_instance = Job.query.filter_by (id = jobid).first()
        if job_instance is not None:
            drone_instance = Drone.query.filter_by (id = job_instance.id).first ()
            payload_instance = Payload.query.filter_by (id = job_instance.payload_id).first()
            return render_template ('flytgcs_web/app.html',job = job_instance)
        else:
            return "<h3>Something went wrong</h3>"
    else:
        return redirect ('/gcslogin',code = 302)


@app.route ('/jobcontrol')
def jobtakeoff ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        jobid = int(request.args.get ('job'))
        job_instance = Job.query.filter_by (id = jobid).first()
        if job_instance is not None:
            drone_instance = Drone.query.filter_by (id = job_instance.id).first ()
            return render_template ('flytgcs_web/flightcontrol.html',drone = drone_instance)
        else:
            return "<h3>Something went wrong</h3>"
    else:
        return redirect ('/gcslogin',code = 302)


'''
----------------------------------------------------------------
INCIDENT TRACKER
----------------------------------------------------------------
'''
@app.route ('/incidents')
def incident_landing ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        incidents = Incident.query.all ()
        length = len (incidents)
        return render_template ('incidents/index.html',incidents = incidents,length = length)
    else:
        return redirect ('/gcslogin',code = 302)


@app.route ('/newincidentreport')
def new_incident ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        drones = Drone.query.all ()
        return render_template ('incidents/newincident.html',drones = drones,priority_list = priority_list)
    else:
        return redirect ('/gcslogin',code = 302)

@app.route ('/newincidentaction',methods=["POST"])
def new_incident_action ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        incident_title = request.form.get ('title')
        incident_title = incident_title.strip ()

        description = request.form.get ('description').strip()
        description = description.strip ()
        username_val = session ['gcs_user']
        drone_sel_id = int(request.form.get ('drone_select'))
        username_id = GCSUser.query.filter_by (username = username_val).first().id
        drone_sel_name = Drone.query.filter_by (id = drone_sel_id).first ().drone_name

        priority_sel = request.form.get ('priority_sel')
        incident = Incident (incident_title,description,username_id,username_val,
                drone_sel_id,drone_sel_name,priority_sel)
        db.session.add (incident)
        db.session.commit ()
        return redirect ('/incidents',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)

@app.route ('/incidentview')
def view_incidents ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        if 'id' in request.args:
            incident_id = int (request.args.get ('id'))
            incident_instance = Incident.query.filter_by (id = incident_id).first ()
            
            drones = Drone.query.all ()
            if incident_instance is None:
                return "<h2>FATAL ERROR</h2>"
            else:
                return render_template ('incidents/view.html',incident = incident_instance,drones = drones,status_list = status_list,
                        priority_list = priority_list)
        else:
            return redirect ('/incidents',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)


@app.route ('/newincidentupdate',methods=['POST'])
def update_incidents ():
    if request.method == "POST":
        if 'gcs_user' in session and session['gcs_logged_in']:
            inc_id = int (request.form.get ('i_id'))
            inc_instance = Incident.query.filter_by (id = inc_id).first ()
            n_desc = request.form.get ('description')
            n_desc = n_desc.strip ()
            inc_instance.description = n_desc
           
            n_title = request.form.get ('title')
            n_title = n_title.strip ()
            inc_instance.title = n_title

            n_drone_sel = int (request.form.get ('drone_select'))
            n_drone_name = Drone.query.filter_by (id = n_drone_sel).first().drone_name
            inc_instance.drone_relatedId = n_drone_sel
            inc_instance.drone_relatedName = n_drone_name
            
            n_status_sel = request.form.get ('status_select')
            inc_instance.status = n_status_sel

            db.session.commit ()

            return redirect ('/incidents',code = 302)
        else:
            return redirect ('/gcslogin',code = 302)
    else:
        return redirect ('/incidents',code = 302)


'''
-----------------------------------------------------------------
DOCUMENTATION/SPHINX
-----------------------------------------------------------------
'''
@app.route ('/docs',defaults={'filename':'index.html'})
@app.route ('/doc/<path:filename>')
def doc (filename):
    return send_from_directory (
            app.config["DOC_FOLDER"],
            filename
            )

'''
-----------------------------------------------------------------
ERROR HANDLER/SPECIAL FUNCTIONS
-----------------------------------------------------------------
'''
@app.errorhandler (404)
def page_not_found (e):
    return render_template ('404.html',code=404)



'''
=======================================================================
=======================================================================
CUSTOMER ACTIONS
=======================================================================
=======================================================================

---------------------------------------------------------------
CUSTOMER LANDING PAGE
---------------------------------------------------------------
'''
@app.route ('/customerportal')
def customer_landing ():
    return render_template ('customerhome.html')

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
