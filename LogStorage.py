from models import GCSUser,Drone,Payload,LogFile
from flask import render_template, redirect, url_for, send_from_directory
import FMSGeneric as fmg

def allowed_file (filename):
    return '.' in filename and \
            filename.rsplit ('.',1)[1].lower () in ['csv','CSV']

def logFileStoragePage (session,request):
    if fmg.isValidSession (session):
        files = LogFile.query.all ()
        return render_template ('LogStorage/index.html',files = files,
                length = len (files))
    else:
        session ['src_url'] = '/logfilestorage'
        return redirect ('/gcslogin?redirect')

def newFilePage (session,request):
    if fmg.isValidSession (session):
        drones = Drone.query.all ()
        return render_template ('LogStorage/newfile.html',drones = drones)
    else:
        session ['src_url'] = '/newlogupload'
        return redirect ('/gcslogin?redirect')

def newFileAction (session,request,db,mongo):
    if fmg.isValidSession (session) and request.method == 'POST':
        if not 'file' in request.files:
            return 'error:no file'
        inputfile = request.files.get ('file')
        drone_id = int (request.form.get ('drone_select'))
        drone_name = Drone.query.filter_by (id = drone_id).first ().drone_name
        if drone_name is None:
            return "ERROR!!"
        if allowed_file (inputfile,filename):
            username = session ['gcs_user']
            user_id = GCSUser.query.filter_by (username = username).first ().id
            blob = inputfile.read ()
            fsize = len (blob)
            log_instance = LogFile (inputfile.filename,user_id,username,
                    drone_id,drone_name,fsize)

            mongo.save_file (inputfile.filename,inputfile,base = 'logfiles')
            db.session.add (log_instance)
            db.session.commit ()
            return redirect ('/logfilestorage')
        else:
            return "Invalid file format"
    else:
        return redirect ('/gcslogin')

def downloadLogFile (session, request,mongo):
    if fmg.isValidSession (session):
        if 'id' not in request.args:
            return "ERROR"
        fileId = int (request.args.get ('id'))
        file_instance = LogFile.query.filter_by (id = fileId).first ()
        fname = file_instance.filename
        return redirect ('/file/' + fname)
    else:
        session ['src_url'] = '/logfilestorage'
        return redirect ('gcslogin?redirect')
