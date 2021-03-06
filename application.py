#!/fsr/bin/env python3
'''
------------------------------------------------------------------------------------------------------
Main GCS applicationlication source code for Redwing Aerospace Laboratories
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
from models import db,GCSUser,Drone,Job,Payload,Incident,LogFile,Pilot, RegisteredFlightModule,RegisteredFlightModuleProvider
from flask_pymongo import PyMongo
import pandas as pd


UPLOADS_FOLDER = '/var/www/html/web-gcs/uploads/'           # deprecated. No longer valid
ALLOWED_LOGS_EXTENSIONS = set (['csv'])                     # Extensions set for log file upload
ALLOWED_BATCH_INVENTORY_TYPES  = ALLOWED_LOGS_EXTENSIONS    # Batch Inventory Uploads also accept only CSV files

status_list = ['Pending Action','Resolved']
priority_list = ['Low','Medium','High']

application = Flask (__name__)
application.config['DEBUG'] = True
application.config['SECRET_KEY'] = b'\xad]\xb8\xcf\x85\xe0\x0cp\xecf\x8ez\x86\x9d\x16%\xa5F\x08\x9c\xb6\x11\xc2\x86'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True


# If PROD available in ENVIRONMENT set mode to development
# Else set mode to production
# TODO:Set opposite ENV variables for mode selection
if os.environ.get('ENV') == 'prod':
    application.config['UPLOAD_FOLDER'] = "uploads/"
    application.config['ENV'] = 'development'
    application.config['DEBUG'] = True
    application.config['TESTING'] = True
else:
    application.config['UPLOAD_FOLDER'] = UPLOADS_FOLDER
    application.config['ENV'] = 'production'
    application.config['DEBUG'] = False
    application.config['TESTING'] = False


# POSTGRES values,credentials and connection
# TODO:Set this in separate configuration file, not in source code
POSTGRES = {
        'user': 'postgres',
        'pw': 'redwingpostgres',
        'db': 'redwingdb',
        'host':'redwingdb.c00t7mbjsni2.ap-south-1.rds.amazonaws.com',
        'port':'5432',
}

application.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
application.config['WTF_CSRF_ENABLED'] = True

# MONGO URI(DISABLED)
application.config ['MONGO_URI'] = 'mongodb://localhost:27017/redwingdb'
application.config ["ACCEPTABLE_COLUMNS"] = ['type','item','storage_type','item_type','weight',
        'uom','stock','value']


# Start application and database instances
db.app = application
db.init_app (application)

mongo = PyMongo (application)
mongo.init_app (application)

logfile_collection = mongo.db.logfiles

db.create_all ()
db.session.commit ()


'''
---------------------------------------------------
IMAGE UPLOAD LOADING FOR PLOTS AND VISUALIZATIONS
---------------------------------------------------
'''

# Load static image from server to html pages (for visualization tool)
# TODO:Add more comments explaining this.
@application.route ('/image/<path:filename>')
def download_file (filename):
	return send_from_directory (application.config["UPLOAD_FOLDER"],filename)

def allowed_file (filename):
    return '.' in filename and \
            filename.rsplit ('.',1)[1].lower() in ALLOWED_LOGS_EXTENSIONS



'''
---------------------------------------------
LANDING PAGE
---------------------------------------------
'''

# Main Landing Page for FMS
@application.route ('/')
def homepage ():
    return render_template("index.html")
    
  
# Main GCS Page route, redirects to 'gcslogin' if not logged in
@application.route ("/gcsportal",methods=['GET','POST'])
def gcs_home():

    # Check if user is logged into session, if not redirect to login page
    # Else redirect to FMS homepage
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
#TODO: Redirect to referrer when automatically directed to login page after login
@application.route ("/gcslogin")
def gcs_login ():
    if not session.get ('gcs_logged_in'):
        return render_template ("fmsgeneric/gcs_login.html")
    else:
        return redirect ('/gcsportal')

# * GCS Login form action route, accepts only POST requests
# * Accept password and username from login page and verify
# salted password with database
@application.route ("/gcsloginform",methods=['POST'])
def gcs_login_action ():

    # Fetch username and password from request form
    usernameval = request.form['username']
    pwval = request.form['password']

    # Check if entered user matching username actually exists
    # If not return error
    qresult = GCSUser.query.filter_by (username=usernameval).first()
    if qresult is None:
        return render_template ("fmsgeneric/gcs_login.html",result="error")

    # If user matched, fetch salt and salted password from database
    qpassword = qresult.password
    qsalt = qresult.salt

    # Verify salt with user-input password
    if verify_password (qpassword,pwval,qsalt):
        session['gcs_logged_in'] = True
        session['gcs_user'] = usernameval
        session.modified = True
        return redirect ('/gcsportal',code = 302)
    else:
        return render_template ("fmsgeneric/gcs_login.html", result="error")

# * Show user profile and account settings
@application.route ("/gcsuserprofile",methods=['POST','GET'])
def show_userprofile():
    if 'gcs_user' in session and session['gcs_logged_in']:
        updated = 0
        if 'updated' in request.args:
            updated = 1

        # * Set 'updated' = 1 if user has made changes to reload page with
        # 'updated' message

        user = session['gcs_user']
        qresult = GCSUser.query.filter_by(username=user).first()
        return render_template ("fmsgeneric/gcsprofile.html",
                username = qresult.username, firstname = qresult.firstname,
                lastname = qresult.lastname,email_id = qresult.email_id,
                updated = updated)

    else:
        return redirect ("/gcslogin",code=302)

# Log out route
@application.route ("/gcslogout",methods=['POST','GET'])
def gcs_logout ():
    # If user is logged in , initiate session log out
    # Delete 'gcs_user' and set 'gcs_logged_in' to False in session
    if 'gcs_user' in session and session ['gcs_logged_in']:
        del session['gcs_user']
        session['gcs_logged_in'] = False

    # Else simply redirect to FMS Home
    return redirect ("/", code=302)

# GCS Sign up page route
@application.route ("/gcssignup",methods=['POST','GET'])
def gcs_signup ():
    return render_template ("fmsgeneric/gcs_signup.html")

# GCS Sign up page form action route
@application.route ("/gcssignupform",methods=['POST'])
def gcs_signup_action ():

    # Generate salt using uuid and hex
    salt = uuid.uuid4().hex

    # Hash and salt password
    pwd_hash = hash_password (request.form['password'].strip(),salt)

    # * Check if username is already taken
    # * If match, reload page with error message
    # * Else, initiate signup
    match = GCSUser.query.filter_by (username = request.form['username']).first()
    if match is None:

        # Sanitize input strings by removing trailing and leading spaces
        username = request.form['username'].strip ()
        firstname = request.form['firstname'].strip ()
        lastname = request.form['lastname'].strip ()
        email_id = request.form['email_id'].strip ()

        # Create new GCS User and add to database
        gcsuser_instance = GCSUser (username = username,password = pwd_hash,
            salt = salt, firstname = firstname, lastname = lastname, 
            email_id = email_id)
        db.session.add (gcsuser_instance)
        db.session.commit ()
        return redirect ("/gcslogin",code=302)
    else:
        return render_template ("fmsgeneric/gcs_signup.html",result = "error")

# POST route for editing GCS profile
@application.route ("/gcsprofileedit",methods=['POST'])
def gcs_profile_edit ():

    # If request is POST, proceed
    if request.method == 'POST': 

        # Check if user is logged in session
        if 'gcs_user' in session['gcs_logged_in']:

            # Iteratively check each field for update and make changes to 
            # user instance manually

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
                
            # Commit changes to database and redirect to profile page
            # With 'updated' flag
            
            db.session.commit()
            return redirect ("/gcsuserprofile?updated",code=302)
    else:
        return redirect ('/gcslogin',code = 302)


# Route for password change input form
@application.route ("/updatepassword")
def change_password ():
    if 'gcs_logged_in' in session and session ['gcs_logged_in']:
        err = False
        if 'error' in request.args:
            err = True
        if err:
            return render_template ("fmsgeneric/changepassword.html",result="error")
        else:
            return render_template ("fmsgeneric/changepassword.html")
    else:
        return redirect ("/gcslogin",code=302)

# Form action route for /updatepasswordi
# If user entered password matches salt in database, update hash
@application.route ("/updatepassword_action",methods=['POST'])
def update_password_action ():
    if request.method == 'POST':
        if 'gcs_user' in session and session['gcs_logged_in']:
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
@application.route ("/dronemonitor")
def show_drones():
    if 'gcs_user' in session:
        drones = Drone.query.all ()
        count = len(drones)
        return render_template ("drone/index.html", drones = drones, count = count)
    else:
        return redirect ("/gcslogin", code=302)

# Route for adding new drone
@application.route ("/newdrone")
def new_drone ():
    if 'gcs_user' in session:
        return render_template ("drone/newdrone.html")
    else:
        return redirect ('/gcslogin',code=302)

# New drone input form action route
@application.route ("/newdroneaction",methods=['POST'])
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


# Edit details of a drone
@application.route ('/editdrone')
def edit_drone ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        drone_id = int (request.args.get ('drone'))
        rfms = RegisteredFlightModule.query.all ()
        drone = Drone.query.filter_by (id = drone_id).first ()
        return render_template ('drone/editdrone.html',drone = drone,rfms = rfms)
    else:
        return redirect ('/gcslogin',code = 302)

@application.route ('/editdroneaction')
def edroneaction ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        return "WIP"
    else:
        return redirect ('/gcslogin',code = 302)
        
# View particular drone
@application.route ("/droneview")
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
                jobslist.applicationend (job)
        
        count = len(jobslist)
        
        if 'error' in request.args:
            strerr = 'deleteerror'
        else:
            strerr = 'noerror'
        return render_template ("drone/droneview.html",drone = drone_instance,jobs = jobslist,count = count,error = strerr)
    else:
        return redirect ('/gcslogin',code = 302)

# Disable drone
@application.route ("/disabledrone")
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
@application.route ('/logfilestorage')
def logfilestorage ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        return  "<h2 style='text-align:center;'>This Feature is currently OFF</h2>"
        '''
        files = LogFile.query.all ()
        length = len(files)
        return render_template ('LogStorage/index.html',files = files,length = length)
        '''
    else:
        return redirect ('/gcslogin',code = 302)

@application.route ('/newlogupload')
def newfile ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        drones = Drone.query.all ()
        return render_template ('LogStorage/newfile.html',drones = drones)
    else:
        return redirect ('/gcslogin',code = 302)

@application.route ('/newfileaction',methods=['POST'])
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

@application.route ('/file/<filename>')
def file (filename):
    return mongo.send_file (filename,base = 'logfiles')

@application.route ('/logdownload')
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
@application.route ('/inventory')
def main_inventory ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        payloads = Payload.query.all ()
        count = len (payloads)
        return render_template ("inventory/index.html",inventory = payloads,count = count)
    else:
        return redirect ('/gcslogin',code = 302)

#@application.route ('/inventoryitem')
#def edit_inventory_item (methods=['GET']):

@application.route ('/addinventory')
def new_inventory ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        payloads = Payload.query.all ()
        return render_template ('inventory/newinventory.html')
    else:
        return redirect ('/gcslogin',code = 302)


@application.route ('/newinventoryaction',methods=['POST'])
def inventoryformaction ():
    if request.method == 'POST':
        if 'gcs_user' in session and session ['gcs_logged_in']:
            type_str = request.form ['type']

            item= request.form ['item']

            storage_type = request.form ['storageType']

            item_type = request.form['itemType']
            item_weight = request.form['weight']
            
            uom = request.form['uom']

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
   
@application.route ('/batchinventoryupload',methods=['GET'])
def batchupload_page ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        return render_template ('inventory/batchinventory_upload.html')
    else:
        return redirect ('/gcslogin',code = 302)


def csv_allowed_file (filename):
    return '.' in filename and  \
            filename.rsplit ('.',1)[1].lower() in ALLOWED_BATCH_INVENTORY_TYPES

@application.route ('/batchinventoryaction',methods=['POST'])
def batchinventory_action ():
    if request.method == 'POST':
        if 'gcs_user' in session and session ['gcs_logged_in']:
            if not 'file' in request.files:
                return 'error:no file'
            inputfile = request.files.get ('file')
            if inputfile is None:
                return "Error!"
            if csv_allowed_file (inputfile.filename):
                filename = inputfile.filename
                outpath = os.path.join (application.config['UPLOAD_FOLDER'],filename)
                inputfile.save (outpath)
                df = pd.read_table (outpath,sep=',')
                read_columns = list (df.columns.values)
                if Counter (read_columns) == Counter (application.config['ACCEPTABLE_COLUMNS']):
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



@application.route ('/inventoryitem',methods=['GET'])
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
@application.route ('/map')
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
@application.route ('/logplotter')
def visualize_logs_input ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        return render_template ('visualize_input.html',parameters = visualise.params_list)
    else:
        return redirect ('/gcslogin',code = 302)

@application.route ('/visualizefile',methods=['GET','POST'])
def visualize_logs ():
    if request.method == 'POST':
        if 'gcs_user' in session and session['gcs_logged_in']:
            if not 'file' in request.files:
                return 'error:no file'
            inputfile = request.files.get ('file')
            if allowed_file (inputfile.filename):
                filename = inputfile.filename
                s_param = request.form.get ('para_select')
                outpath = os.path.join (application.config['UPLOAD_FOLDER'],filename)
                imgpath = os.path.join (application.config['UPLOAD_FOLDER'],'plot.png')
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


@application.route ('/logfileupload')
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
@application.route ('/npntauthentication')
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
@application.route ("/jobtracker")
def show_jobs ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        jobs = Job.query.all()
        count = len(jobs)
        return render_template ("jobs/jobs.html", deployments = jobs, length = count)
    else:
        return redirect ('/gcslogin',code = 302)
            
# Form page for adding new job
@application.route ("/newdeployment")
def new_job ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        drones = Drone.query.all()
        payloads = Payload.query.all ()
        return render_template ('jobs/newjob.html',drones = drones,payloads = payloads)
    else:
        return redirect ('/gcslogin',code = 302)

# Form action route for adding new job/deployment
@application.route ('/newjobform',methods=['POST'])
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
@application.route ('/filterjobs',methods=['POST'])
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
@application.route ('/jobview')
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
                        return render_template ('jobs/jobview.html',jobid = job_instance.id)
                    else:
                        return "<h2>Work In Progress</h2>"
                else:
                    return redirect ('/jobtracker',code = 302)
        else:
            return "<h2 style='text-align:center;'>ERROR,Something went wrong</h2>"
    else:
        return redirect ('/gcslogin',code = 302)

# OTP form action route
@application.route ('/jobotpauth',methods=['POST'])
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
@application.route ('/initiatedeployment',methods=['POST'])
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


@application.route ('/godeployment')
def go_deployment ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        jobid = int (request.args.get ('job'))
        job_instance = Job.query.filter_by (id = jobid).first()
        if job_instance is not None:
            drone_instance = Drone.query.filter_by (id = job_instance.id).first ()
            payload_instance = Payload.query.filter_by (id = job_instance.payload_id).first()
            return render_template ('flytgcs_web/application.html',job = job_instance)
        else:
            return "<h3>Something went wrong</h3>"
    else:
        return redirect ('/gcslogin',code = 302)


@application.route ('/jobcontrol')
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
@application.route ('/incidents')
def incident_landing ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        incidents = Incident.query.all ()
        length = len (incidents)
        return render_template ('incidents/index.html',incidents = incidents,length = length)
    else:
        return redirect ('/gcslogin',code = 302)


@application.route ('/newincidentreport')
def new_incident ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        drones = Drone.query.all ()
        return render_template ('incidents/newincident.html',drones = drones,priority_list = priority_list)
    else:
        return redirect ('/gcslogin',code = 302)

@application.route ('/newincidentaction',methods=["POST"])
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

@application.route ('/incidentview')
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


@application.route ('/newincidentupdate',methods=['POST'])
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
---------------------------------------------------------------
PILOT
--------------------------------------------------------------
'''
@application.route ('/pilotdb')
def view_pilots ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        pilots = Pilot.query.all ()
        count = len (pilots)
        gcsusers = GCSUser.query.all ()
        gcspair = []
        for g in gcsusers:
            gcspair.append ([g.id,g.username])
        if request.args.get ('error'):
            return render_template ('pilots/index.html',pilots = pilots,count = count,error=1,gcspair = gcspair)
        else:
            return render_template ('pilots/index.html',pilots = pilots,count = count,error=0, gcspair = gcspair)
    else:
        return redirect ('/gcslogin',code = 302)


@application.route ('/newpilotform',methods=['POST'])
def new_pilot_action ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        gcs_id = int (request.form.get('gcsuser_id'))
        match_pilot = Pilot.query.filter_by ( gcsuser_id = gcs_id).first()
        if match_pilot is not None:
            return redirect ('/pilotdb?error')
        else:
            pilot = Pilot (gcs_id)
            db.session.add (pilot)
            db.session.commit ()
            return redirect ('/pilotdb')

'''
----------------------------------------------------------------
REGISTERED FLIGHT MODULE
----------------------------------------------------------------
'''
@application.route ('/registeredfm')
def rfm_index ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        rfms = RegisteredFlightModule.query.all ()
        count = len (rfms)
        return render_template ('rfm/index.html',rfms = rfms,count = count)
    else:
        return redirect ('/gcslogin',code = 302)

@application.route ('/newrfm')
def newrfm ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        rfmps = RegisteredFlightModuleProvider.query.all ()
        return render_template ('rfm/newrfm.html',rfmps = rfmps)
    else:
        return redirect ('/gcslogin',code = 302)

@application.route ('/newrfmaction',methods=['POST'])
def rfmaction ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        rfmname = request.form.get ('rfmname')
        rfmuid = request.form.get ('rfmuid')
        hardwarespecs = request.form.get ('hardwarespecs')
        clevel = int (request.form.get ('clevel'))
        fwhash = request.form.get ('fwhash')
        hwuid = request.form.get ('hwuid')
        rfmp_id = int (request.form.get('rfmp_select'))
        rfm = RegisteredFlightModule (rfmname,rfmuid,hardwarespecs,rfmp_id,
                clevel,fwhash,hwuid)
        db.session.add (rfm)
        db.session.commit ()
        return redirect ('/registeredfm',code = 302)

'''
-------------------------------------------------------------------
REGISTERED FLIGHT MODULE PROVIDER
-------------------------------------------------------------------
'''
@application.route ('/registeredfmprovider')
def rfmp_index ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        rfmps = RegisteredFlightModuleProvider.query.all ()
        count = len (rfmps)
        return render_template ('rfmp/index.html',count = count,rfmps = rfmps)
    else:
        return redirect ('/gcslogin',code = 302)

@application.route ('/newrfmpaction',methods=['POST'])
def newrfmpaction ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        rfmpname = request.form.get ('rfmpname')
        rfmp = RegisteredFlightModuleProvider (rfmpname)
        db.session.add (rfmp)
        db.session.commit ()
        return redirect ('/registerdfmprovider')
    else:
        return redirect ('/gcslogin',code = 302)


'''
-----------------------------------------------------------------
ERROR HANDLER/SPECIAL FUNCTIONS
-----------------------------------------------------------------
'''
@application.errorhandler (404)
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
@application.route ('/customerportal')
def customer_landing ():
    return render_template ('customerhome.html')

'''
-------------------------------------------------------------------
RESTful API 
-------------------------------------------------------------------
'''

# Test GET route to test API
@application.route ("/api/v1/test")
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
    application.run (debug = True)
