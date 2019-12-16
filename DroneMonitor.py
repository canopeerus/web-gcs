from models import Drone,Payload,Job,RegisteredFlightModule
import FMSGeneric as fmg
import MiscHelper
from flask import render_template,redirect,url_for,send_from_directory


def listAllDrones (session,request):
    if fmg.isValidSession (session):
        drones = Drone.query.all ()
        return render_template ("drone/index.html",drones = drones,count = len(drones))
    else:
        session ['src_url'] = '/dronemonitor'
        return redirect ('/gcslogin?redirect',code = 302)

def newDronePage (session,request):
    if fmg.isValidSession (session):
        rfms = RegisteredFlightModule.query.all ()
        return render_template ('drone/newdrone.html',rfms = rfms)
    else:
        session ['src_url'] = '/newdrone'
        return redirect ('/gcslogin',code = 302)

def newDroneAction (session,request,db):
    if fmg.isValidSession (session) and request.method == 'POST':
        drone = Drone (drone_name = request.form['droneName'],
                motor_count = request.form['motorCount'],
                model = request.form['droneModel'],
                battery_type = request.form['batteryType'],
                rfm_id = int(request.form['rfm_select']))
        db.session.add (drone)
        db.session.commit ()
        return redirect ('/dronemonitor',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)

def editDronePage (session,request):
    if fmg.isValidSession (session):
        drone_id = int (request.args.get ('drone'))
        registered_fm_list = RegisteredFlightModule.query.all ()
        drone = Drone.query.filter_by (id = drone_id).first ()
        return render_template ('drone/editdrone.html',drone = drone,
                rfms = registered_fm_list,username = session ['gcs_user'])
    else:
        session ['src_url'] =  '/editdrone'
        return redirect ("/gcslogin?redirect",code = 302)

def editDroneAction (session,request,db):
    if fmg.isValidSession (session) and request.method == 'POST':
        return "WIP"
    else:
        return redirect ('/gcslogin',code = 302)

def viewSpecificDrone (session,request):
    if fmg.isValidSession (session):
        return "ERROR .... work in Progress!"
        '''
        if 'drone' in request.args:
            drone_arg = request.args.get ('drone')
            if drone_arg == 'undefined' or drone_arg is None:
                return "<h2>Something went wrong!</h2>"

            r_drone_id = int (drone_arg)
            drone_match = Drone.query.filter_by (id = r_drone_id).first ()
            if drone_match is None:
                return "<h2>Argument mismatch</h2>"
            jobslist = []
            if drone_match.has_jobs_scheduled ():
                id_array = drone_match.job_queue_int ()
                print ("array")
                print (id_array)
                for iden in id_array:
                    print(iden)
                    job = Job.query.filter_by (id = iden).first ()
                    if job is None:
                        return "The fuclLLL"
                    jobslist.append (job)
            
            if 'error' in request.args:
                strerr = 'deleteerror'
            else:
                strerr = 'noerror'
            return render_template ('drone/droneview.html',drone = drone_match,
                    jobs = jobslist,count = len(jobslist),error = strerr)
        else:
            return "ERROR"
        '''
    else:
        session ['src_url'] = '/droneview'
        return redirect ('/gcslogin?redirect',code = 302)

def terminateDrone (session,request,db):
    if fmg.isValidSession (session):
        if 'drone' in request.args:
            r_drone_id = int (request.args.get ('drone'))
            drone = Drone.query.filter_by ( id = r_drone_id).first ()
            if drone.disable ():
                return redirect ('/dronemonitor',code = 302)
            else:
                return redirect ('/droneview?error&drone='+str(r_drone_id),
                        code = 302)
        else:
            return "ERROR"
    else:
        session ['src_url'] = '/dronemonitor'
        return redirect ('/gcslogin?redirect',code = 302)
