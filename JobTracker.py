'''
--------------------------------------------------------------------------
Specific module source code for operations related to Job/Deployments
--------------------------------------------------------------------------
'''

import base64
import decimal
import os
from xml.etree.ElementTree import Element, SubElement, ElementTree
import uuid

import cryptography
import signxml as sx
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import pkcs1_15
from lxml import etree

from models import Job,Drone,Payload
import FMSGeneric as fmg,datetime
import MiscHelper,json

from flask import render_template,redirect,url_for,send_from_directory

def listAllJobs (session,request,flag):
    if fmg.isValidSession (session):
        jobs = Job.query.all ()
        if flag == 'npnt':
            template_str = 'npnt/index.html'
        else:
            template_str = 'jobs/jobs.html'
        return render_template (template_str,deployments = jobs,
                length = len (jobs),username = session ['gcs_user'])
    else:
        if flag == 'npnt':
            session ['src_url'] = '/npntauthentication'
        else:
            session ['src_url'] = '/jobtracker'
        return redirect ("/gcslogin?redirect",code = 302)

def scheduleNewJobPage (session,request):
    if fmg.isValidSession (session):
        drones = Drone.query.all ()
        payloads = Payload.query.all ()
        return render_template ('jobs/newjob.html',drones = drones,
                payloads = payloads, username = session ['gcs_user'])
    else:
        session ['src_url'] = '/newdeployment'
        return redirect ('/gcslogin?redirect',code = 302)

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
        count = int (request.form.get ('count'))
        max_alt_ft = float (request.form.get ('max_alt'))
        geofence_lat = MiscHelper.getCoordsFloatList (
                request.form.get ('geofence_lat'))
        geofence_lon = MiscHelper.getCoordsFloatList (
                request.form.get ('geofence_lon'))

        origin_lon = float (request.form.get ('origin_lon'))
        origin_lat = float (request.form.get ('origin_lat'))
        dest_lon = float (request.form.get ('dest_lon'))
        dest_lat = float (request.form.get ('dest_lat'))

        job_instance = Job (sdatetime_sel,edatetime_sel,drone_id,geofence_lat,
                geofence_lon,int (payload_id), count, max_alt_ft,
                origin_lat,origin_lon,dest_lat,dest_lon)

        db.session.add (job_instance)
        db.session.commit ()

        return redirect ('/jobtracker',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)

def jobViewPage (session,request,flag = 'job'):
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
                        if flag == 'npnt':
                            template_str = 'npnt/jobview.html'
                        else:
                            template_str = 'jobs/jobview.html'
                        return render_template (template_str,drone_name = 
                                drone_instance.drone_name,payload_name = payload.item,
                                job = job_instance,username = session ['gcs_user'])
                    else:
                        return  "<h2>Work In Progress</h2>"
                else:
                    return redirect ('/jobtracker',code = 302)
        else:
            return "<h2>ERROR!!!!</h2>"
    else:
        if flag == 'job':
            session ['src_url'] = '/jobview'
        else:
            session ['src_url'] = '/jobviewnpnt'

        return redirect ('/gcslogin',code = 302)

def goDeploymentDict (session,request):
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

            return perm_request
        else:
            return "<h3>Something went wrong</h3>"
    else:
        session ['src_url'] = '/godeployment'
        return redirect ('/gcslogin?error',code = 302)

def goDeployment (session,request):
    if fmg.isValidSession (session):
        return json.dumps (goDeploymentDict (session,request),indent = 4)
    else:
        return redirect ('/gcslogin')

def verify_xml_signature (xml_file):
    """
    Verify the signature of a given xml file against a certificate
    :param path xml_file: path to the xml file for verification
    :param certificate_path: path to the certificate to be used for verification
    :return: bool: the success of verification
    """
    # TODO -  refactor such that this verifies for generic stuff
    tree = etree.parse(xml_file)
    root = tree.getroot()
    certificate = ''
    for x in root:
        certificate = x.find ('X509Certificate')

    try:
        verified_data = sx.XMLVerifier().verify(data=root, require_x509=True, x509_cert=certificate).signed_xml
        # The file signature is authentic
        return True
    except cryptography.exceptions.InvalidSignature:
            # print(verified_data)
            # add the type of exception
        return False
