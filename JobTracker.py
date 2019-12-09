'''
--------------------------------------------------------------------------
Specific module source code for operations related to Job/Deployments
--------------------------------------------------------------------------
'''

from models import Job,Drone,Payload
import FMSGeneric as fmg,datetime
import MiscHelper,json
from flask import render_template,redirect,url_for,send_from_directory

def listAllJobs (session,request):
    if fmg.isValidSession (session):
        jobs = Job.query.all ()
        return render_template ('jobs/jobs.html',deployments = jobs,
                count = len (jobs))
    else:
        return redirect ("/gcslogin",code = 302)

def scheduleNewJobPage (session,request):
    if fmg.isValidSession (session):
        drones = Drone.query.all ()
        payloads = Payload.query.all ()
        return render_template ('jobs/newjob.html',drones = drones,
                payloads = payloads)
    else:
        return redirect ('/gcslogin',code = 302)

def scheduleNewJobAction (session,request,db):
    if request.method == 'POST' and fmg.isValidSession (session):
        sdate_sel = request.form.get ('startdate')
        stime_sel = request.form.get ('starttime')
        edate_sel = request.form.get ('enddate')
        etime_sel = request.form.get ('endtime')
        sdatetime_sel = MiscHelper.dateTimeMerge (sdate_sel,stime_sel)
        edatetime_sel = MiscHelper.dateTimeMerge (edate_sel,etime_sel)
        drone_id = int (str (request.form.get ('drone_select')))
        payload_id = int(request.form.get ('payload_select'))
        max_alt_ft = float (request.form.get ('max_alt'))
        geofence_lat = MiscHelper.getCoordsFloatList (
                request.form.get ('geofence_lat'))
        goefence_lon = MiscHelper.getCoordsFloatList (
                request.form.get ('geofence_lon'))
        dest_lon = float (request.form.get ('dest_lon'))
        dest_lat = float (request.form.get ('dest_lat'))

        job_instance = Job (sdatetime_sel,edatetime_sel,drone_id,geofence_lat,
                geofence_long,int (payload_id), count, max_alt_ft,
                origin_lat,origin_lon,dest_lat,dest_lon)

        db.session.add (job_instance)
        db.session.commit ()

        return redirect ('/jobtracker',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)

def jobViewPage (session,request):
    if fmg.isValidSession (session):
        if 'job' in request.args:
            jobid_str = request.args.get ('job')
            if jobid_str == 'undefined' or jobid_str is None:
                return "<h2 style='text-align:center;'>The request was not understood</h2>"
            else:
                jobid = int (jobid_str)
                job_instance = Job.query.filter_by (id = jobid).first ()
                if job_instance is not None:
                    drone_instance = job_instance.get_assigned_drone ()
                    payload = job_instance.get_assigned_payload ()
                    if job_instance.is_pending ():
                        return render_template ('jobs/jobview.html',drone_name = 
                                drone_instance.drone_name,payload_name = payload.item,
                                job = job_instance)
                    else:
                        return  "<h2>Work In Progress</h2>"
                else:
                    return redirect ('/jobtracker',code = 302)
        else:
            return "<h2>ERROR!!!!</h2>"
    else:
        return redirect ('/gcslogin',code = 302)

def goDeployment (session,request):
    if fmg.isValidSession (session):
        jobid = int (request.args.get ('job'))
        job_instance = Job.query.filter_by (id = jobid).first()
        if job_instance is not None:
            drone_instance = job_instance.get_assigned_drone ()
            payload_instance = job_instance.get_assigned_payload ()

            perm_request = dict()
            perm_request['pilotBusinessIdentifier'] = '1234'
            perm_request['flyArea'] = list()

            for lon,lat in zip (job_instance.geofence_lat,job_instance.geofence_long):
                coords = dict()
                coords['latitude'] = lat
                coords['longitude'] = lon
                perm_request['flyArea'].append (coords)
            perm_request['droneId'] = str (drone_instance.id)
            perm_request['payloadWeightInKg'] = float (job_instance.payload_weight/1000)
            perm_request['payloadDetails'] = payload_instance.item
            perm_request['flightPurpose'] = job_instance.deployment_purpose
            perm_request['startDateTime'] = str(job_instance.startDate)
            perm_request['endDateTime'] = str (job_instance.endDate)

            return json.dumps (perm_request,indent = 4)
        else:
            return "<h3>Something went wrong</h3>"
    else:
        return redirect ('/gcslogin',code = 302)
