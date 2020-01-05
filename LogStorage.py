from models import GCSUser,Drone,Payload,LogFile,Job
from flask import render_template, redirect, url_for, send_from_directory, send_file
import FMSGeneric as fmg
import os

def allowed_file (filename):
    return '.' in filename and \
            filename.rsplit ('.',1)[1].lower () in ['JSON','json']

def logFileStoragePage (session,request):
    if fmg.isValidSession (session):
        files = LogFile.query.all ()
        return render_template ('LogStorage/index.html',files = files,
                length = len (files),username = session ['gcs_user'])
    else:
        session ['src_url'] = '/logfilestorage'
        return redirect ('/gcslogin?redirect')

def newFilePage (session,request):
    if fmg.isValidSession (session):
        drones = Drone.query.all ()
        return render_template ('LogStorage/newfile.html',drones = drones,
                username = session ['gcs_user'])
    else:
        session ['src_url'] = '/newlogupload'
        return redirect ('/gcslogin?redirect')

def newFileAction (session,request,db):
    if fmg.isValidSession (session) and request.method == 'POST':
        if not 'file' in request.files:
            return 'error:no file'
        inputfile = request.files.get ('file')
        job_id = int (request.form.get ('jobid'))
        drone_id = Job.query.filter_by (id = job_id).first ().drone_id
        drone_name = Drone.query.filter_by (id = drone_id).first ().rpa_name
        if drone_name is None:
            return "ERROR!!"
        if allowed_file (inputfile.filename):
            username = session ['gcs_user']
            user_id = GCSUser.query.filter_by (username = username).first ().id
            blob = inputfile.read ()
            fsize = len (blob)
            log_instance = LogFile (inputfile.filename,user_id,
                    drone_id,fsize,blob,job_id)
            

            db.session.add (log_instance)
            db.session.commit ()
            return redirect ('/logfilestorage')
        else:
            return "Invalid file format"
    else:
        return redirect ('/gcslogin')

def downloadLogFile (session, request):
    if fmg.isValidSession (session):
        if 'id' in request.args:
            fileId = int (request.args.get ('id'))
            file_instance = LogFile.query.filter_by (id = fileId).first ()
            if file_instance is None:
                return "ERROR"
            else:
                with open (file_instance.filename,'wb') as f:
                    f.write (file_instance.file_blog)
                resp = send_file (file_instance.filename,
                        mimetype = "text/plain",
                        as_attachment = True,
                        conditional = False)
                os.remove (file_instance.filename)
                resp.headers ['x-suggested-filename'] = file_instance.filename
                return resp
        else:
            return "ID ERROR"
    else:
        return redirect ('/gcslogin')
