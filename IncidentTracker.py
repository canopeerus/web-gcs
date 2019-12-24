from models import GCSUser,Drone,Job,Payload, Incident
import FMSGeneric as fmg
import MiscHelper
from flask import render_template,redirect,url_for,send_from_directory

priority_list= ['Low','Medium','High']
status_list = ['Pending Action','Resolved']

def listAllIncidents (session,request):
    if fmg.isValidSession (session):
        incidents = Incident.query.all ()
        return render_template ('incidents/index.html',incidents = incidents,
                length = len (incidents),username = session ['gcs_user'])
    else:
        session ['src_url'] = '/incidents'
        return redirect ('/gcslogin?redirect')

def newIncidentPage (session,request):
    if fmg.isValidSession (session):
        drones = Drone.query.all ()
        return render_template ('incidents/newincident.html',drones = drones,
                priority_list = priority_list,username = session ['gcs_user'])
    else:
        session ['src_url'] = '/newincidentreport'
        return redirect ('/gcslogin?redirect')

def newIncidentAction (session,request,db):
    if fmg.isValidSession (session) and request.method == 'POST':
        incident_title = request.form.get ('title').strip ()
        description = request.form.get ('description').strip ()
        username_val = session ['gcs_user']
        drone_sel_id = int (request.form.get ('drone_select'))
        username_id = GCSUser.query.filter_by (username = username_val).first ().id
        drone_sel_name = Drone.query.filter_by (id = drone_sel_id).first ().rpa_name
        priority_sel = request.form.get ('priority_sel')
        incident = Incident (incident_title,description,username_id,username_val,
                drone_sel_id,drone_sel_name,priority_sel)
        db.session.add (incident)
        db.session.commit ()
        return redirect ('/incidents')
    else:
        return redirect ('/gcslogin')

def viewIncidentPage (session,request):
    if fmg.isValidSession (session):
        if 'id' in request.args:
            incident_id = int (request.args.get ('id'))
            incident = Incident.query.filter_by (id = incident_id).first ()
            drones = Drone.query.all ()
            if incident is None:
                return "ERROR"
            else:
                return render_template ('incidents/view.html',incident = incident,
                        drones = drones,status_list = status_list,
                        priority_list = priority_list,username = session ['gcs_user'])
        else:
            return redirect ('/incidents')
    else:
        session ['src_url'] = '/incidentview'
        return redirect ('/gcslogin?redirect')

def updateIncidentAction (session,request,db):
    if fmg.isValidSession (session) and request.method == 'POST':
        inc_id = int (request.form.get ('i_id'))
        incident= Incident.query.filter_by (id = inc_id).first ()
        incident.description = request.form.get ('description').strip ()

        incident.title = request.form.get ('title').strip ()
        incident.drone_relatedId = int (request.form.get ('drone_select'))
        incident.drone_relatedName = Drone.query.filter_by (
                id = incident.drone_relatedId).first ().rpa_name
        incident.status = request.form.get ('status_select')

        db.session.commit ()
        return redirect ('/incidents')
    else:
        return redirect ('/gcslogin')
