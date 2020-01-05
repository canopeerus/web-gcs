
'''
------------------------------------------------------------------------------------------------------
Main GCS applicationlication source code for Redwing Aerospace Laboratories
@author : Aditya Visvanathan
@version : 0.1.0
------------------------------------------------------------------------------------------------------
'''

from collections import Counter
from flask import Flask,render_template,redirect,session,abort,request,flash,url_for,send_from_directory,send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os,uuid,visualise,shutil,time,geocoder,json
from authutils import verify_password,hash_password
from models import db,GCSUser,Drone,Job,Payload,Incident,LogFile,Pilot, RegisteredFlightModule,RegisteredFlightModuleProvider
import pandas as pd
import LogStorage,IncidentTracker,JobTracker,DroneMonitor,InventoryMgmt,FMSGeneric as fmg
import urllib,MiscHelper

import base64,decimal,uuid,cryptography,signxml as sx
from lxml import etree
from xml.etree.ElementTree import Element, SubElement, ElementTree

UPLOADS_FOLDER = '/var/www/html/web-gcs/uploads/'           # deprecated. No longer valid
ALLOWED_LOGS_EXTENSIONS = set (['csv'])                     # Extensions set for log file upload
ALLOWED_BATCH_INVENTORY_TYPES  = ALLOWED_LOGS_EXTENSIONS    # Batch Inventory Uploads also accept only CSV files


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
application.config ["ACCEPTABLE_COLUMNS"] = ['type','item','storage_type','item_type',
        'weight','uom','stock','value']


# Start application and database instances
db.app = application
db.init_app (application)



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



@application.route ('/testindex')
def fn ():
    return render_template ("fms_index.html")

'''
---------------------------------------------
LANDING PAGE
---------------------------------------------
'''

# Main Landing Page for FMS
@application.route ('/')
def homepage ():
    return render_template("index.html")
    
  
# Main GCS Page route, redirects to 'gcslogin?redirect' if not logged in
@application.route ("/gcsportal")
def gcs_home():
    return fmg.gcsHome (session,request)
'''
----------------------------------
GCS USER PROFILE ACTIONS
----------------------------------
'''
# GCS Login page route
#TODO: Redirect to referrer when automatically directed to login page after login
@application.route ("/gcslogin")
def gcs_login ():
    return fmg.gcsLoginPage (session,request)

# * GCS Login form action route, accepts only POST requests
# * Accept password and username from login page and verify
# salted password with database
@application.route ("/gcsloginform",methods=['POST'])
def gcs_login_action ():
    return fmg.gcsLoginAction (session,request)

# * Show user profile and account settings
@application.route ("/gcsuserprofile",methods=['POST','GET'])
def show_userprofile():
    return fmg.showUserProfile (session,request)

# Log out route
@application.route ("/gcslogout",methods=['POST','GET'])
def gcs_logout ():
    return fmg.gcsLogout (session,request)

# GCS Sign up page route
@application.route ("/gcssignup",methods=['POST','GET'])
def gcs_signup ():
    return fmg.gcsSignupPage (session,request)

# GCS Sign up page form action route
@application.route ("/gcssignupform",methods=['POST'])
def gcs_signup_action ():
    return fmg.gcsSignupAction (session,request,db)
    
# POST route for editing GCS profile
@application.route ("/gcsprofileedit",methods=['POST'])
def gcs_profile_edit ():
    return fmg.profileEditAction (session,request,db)



# Route for password change input form
@application.route ("/updatepassword")
def change_password ():
    return fmg.gcsUserUpdatePasswordPage (session,request)

# Form action route for /updatepasswordi
# If user entered password matches salt in database, update hash
@application.route ("/updatepassword_action",methods=['POST'])
def update_password_action ():
    return fmg.gcsUserUpdatePasswordAction (session,request,db)

'''
-------------------------------
DRONE ACTION ROUTES
-------------------------------
'''
# Route for drone monitor list screen
@application.route ("/dronemonitor")
def show_drones():
    return DroneMonitor.listAllDrones (session,request)

# Route for adding new drone
@application.route ("/newdrone")
def new_drone ():
    return DroneMonitor.newDronePage (session,request)

# New drone input form action route
@application.route ("/newdroneaction",methods=['POST'])
def add_new_drone():
    return DroneMonitor.newDroneAction (session,request,db)

# Edit details of a drone
@application.route ('/editdrone')
def edit_drone ():
    return DroneMonitor.editDronePage (session,request)

@application.route ('/editdroneaction')
def edroneaction ():
    return DroneMonitor.editDroneAction (session,request,db)

# View particular drone
@application.route ("/droneview")
def individual_drone ():
    return DroneMonitor.viewSpecificDrone (session,request)

# Disable drone
@application.route ("/disabledrone")
def terminate_drone ():
    return DroneMonitor.terminateDrone (session,request)


'''
---------------------------------------
LOG FILE STORAGE DATABASE
---------------------------------------
'''
'''
PAUSE LOGSTORAGE FOR NOW
@application.route ('/logfilestorage')
def logfilestorage ():
    return LogStorage.logFileStoragePage (session,request)

@application.route ('/newlogupload')
def newfile ():
    return LogStorage.newFilePage (session,request)

@application.route ('/newfileaction',methods=['POST'])
def newfileaction ():
    return LogStorage.newFileAction (session,request,db)

@application.route ('/file/<filename>')
def file (filename):
    return mongo.send_file (filename,base = 'logfiles')

@application.route ('/logdownload')
def download_logfile ():
    return LogStorage.downloadLogFile (session, request)
    
'''


'''
--------------------------------
INVENTORY
--------------------------------
'''
# Inventory
@application.route ('/inventory')
def main_inventory ():
    return InventoryMgmt.listAllInventory (session,request)

@application.route ('/addinventory')
def new_inventory ():
    return InventoryMgmt.newInventoryPage (session,request)
        
@application.route ('/newinventoryaction',methods=['POST'])
def inventoryformaction ():
    return  InventoryMgmt.newInventoryAction (session,request,db)

@application.route ('/batchinventoryupload',methods=['GET'])
def batchupload_page ():
    return InventoryMgmt.batchInventoryUploadPage (session,request)

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
            return redirect ('/gcslogin?redirect',code = 302)
    else:
        return "ERROR"



@application.route ('/inventoryitem',methods=['GET'])
def inventoryitemdisplay ():
    return InventoryMgmt.inventoryEditPage (session,request)
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
        return render_template ('maps.html',jobs = jobslist,username = session['gcs_user'])
    else:
        return redirect ('/gcslogin?redirect',code=302)


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
        return redirect ('/gcslogin?redirect',code = 302)

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
            return redirect ('/gcslogin?redirect',code = 302)
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
        return redirect ('/gcslogin?redirect',code = 302)

'''
--------------------------------------
NPNT AUTHENTICATION
--------------------------------------
'''
# NPNT tool page
@application.route ('/npntauthentication')
def npntauthroute ():
    return JobTracker.listAllJobs (session,request,flag='npnt')

@application.route ('/jobviewnpnt')
def jobviewnpnt ():
    return JobTracker.jobViewPage (session,request,flag = 'npnt')

@application.route ('/gonpnt')
def gonpnt ():
    jobid = int (request.args.get ('job'))
    json_dict = JobTracker.goDeploymentDict (session,request)
    return render_template ('npnt/permrequest.html',json = 
            json.dumps (json_dict,indent = 4),jobid = jobid,
            username = session ['gcs_user'])

@application.route ('/sendrequest')
def send_request ():
    if 'gcs_user' in session and session['gcs_logged_in']:
        jobid = int (request.args.get ('job'))
        json_dict = JobTracker.goDeploymentDict (session,request)
        jsondata = json.dumps (json_dict)
        req = urllib.request.Request ('https://digitalsky.dgca.gov.in/api/applicationForm/flyDronePermissionApplication')
        jsondata = jsondata.encode ('utf-8')
        req.add_header ('Content-Type','application/json;charset = utf-8')
        req.add_header ('Content-Length',len (jsondata))
        try:
            resp = urllib.request.urlopen (req,jsondata)
        except urllib.error.HTTPError as e:
            return str (e.__dict__)
        charset = resp.info ().get_content_charset ()
        content = req.read ().decode (charset)
        return content
    else:
        return redirect ('/gcslogin?redirect',code = 302)

@application.route ('/verifyxmlsig')
def xmlVerifyPage ():
    if fmg.isValidSession (session):
        return render_template ("npnt/verifyxml.html")
    else:
        session ['src_url'] = '/verifyxmlsig'
        return redirect ('gcslogin?redirect')

@application.route ('/verifyxmlsigaction',methods = ['POST'])
def xmlverifyaction ():
    if request.method == 'POST' and fmg.isValidSession (session):
        return 'WIP'
        '''
        if not 'file' in request.files:
            return 'error:nofile'
        inputfile = request.files.get ('file')
        inputfile.save (inputfile.filename)
        if MiscHelper.verifyXMLSignature (inputfile.filename):
            print ("Verified")
        else:
            print ("Not verified")
        '''
    else:
        return redirect ('/gcslogin')

'''
---------------------------------------
JOBS/DEPLOYMENT RELATED ACTIONS
---------------------------------------
'''
# Deployment/job tracker
@application.route ("/jobtracker")
def showJobs ():
    return JobTracker.listAllJobs (session,request,flag = 'job')


# Form page for adding new job
@application.route ("/newdeployment")
def newJobPage ():
    return JobTracker.scheduleNewJobPage (session,request)

# Form action route for adding new job/deployment
@application.route ('/newjobform',methods=['POST'])
def newJobAction ():
    return JobTracker.scheduleNewJobAction (session,request,db)

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
            return render_template ('jobs/jobs.html',deployments = jobmatch,
                    username = session ['gcs_user'])
        else:
            return render_template ('jobs/jobs.html',error = 'matcherror',
                    username = session ['gcs_user'])
    else:
        return redirect ('/gcslogin?redirect',code = 302)

# particular Job details view
@application.route ('/jobview')
def jobview ():
    return JobTracker.jobViewPage (session,request)


@application.route ('/godeployment')
def goDeployment ():
    return JobTracker.goDeployment (session,request)

'''
----------------------------------------------------------------
INCIDENT TRACKER
----------------------------------------------------------------
'''
@application.route ('/incidents')
def incident_landing ():
    return IncidentTracker.listAllIncidents (session,request)

@application.route ('/newincidentreport')
def new_incident ():
    return IncidentTracker.newIncidentPage (session,request)

@application.route ('/newincidentaction',methods=["POST"])
def new_incident_action ():
    return IncidentTracker.newIncidentAction (session,request,db)

@application.route ('/incidentview')
def view_incidents ():
    return IncidentTracker.viewIncidentPage (session,request)

@application.route ('/newincidentupdate',methods=['POST'])
def update_incidents ():
    return IncidentTracker.updateIncidentAction (session,request,db)

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
            return render_template ('pilots/index.html',pilots = pilots,
                    count = count,error=1,gcspair = gcspair,
                    username = session ['gcs_user'])
        else:
            return render_template ('pilots/index.html',pilots = pilots,
                    count = count,error=0, gcspair = gcspair,
                    username = session ['gcs_user'])
    else:
        return redirect ('/gcslogin?redirect',code = 302)


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
        return redirect ('/gcslogin?redirect',code = 302)

@application.route ('/newrfm')
def newrfm ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        rfmps = RegisteredFlightModuleProvider.query.all ()
        return render_template ('rfm/newrfm.html',rfmps = rfmps,
                username = session ['gcs_user'])
    else:
        return redirect ('/gcslogin?redirect',code = 302)

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
        return render_template ('rfmp/index.html',count = count,rfmps = rfmps,
                username = session ['gcs_user'])
    else:
        return redirect ('/gcslogin?redirect',code = 302)

@application.route ('/newrfmpaction',methods=['POST'])
def newrfmpaction ():
    if 'gcs_user' in session and session ['gcs_logged_in']:
        rfmpname = request.form.get ('rfmpname')
        rfmp = RegisteredFlightModuleProvider (rfmpname)
        db.session.add (rfmp)
        db.session.commit ()
        return redirect ('/registerdfmprovider')
    else:
        return redirect ('/gcslogin?redirect',code = 302)


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
