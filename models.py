# Describes models for various entities in the GCS

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from queue import Queue
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm.attributes import flag_modified
import geocoder
db = SQLAlchemy ()

class RegisteredFlightModuleProvider (db.Model):
    __tablename__ = 'rfmproviders'
    id = db.Column (db.Integer,primary_key = True)
    rfmp_name = db.Column (db.String())
    
    def __init__ (self,rfmpname):
        self.rfmp_name = rfmpname

class RegisteredFlightModule (db.Model):
    __tablename__ = 'rfmodules'
    id = db.Column (db.Integer,primary_key = True)
    rfm_name = db.Column (db.String())
    rfm_unique_id = db.Column (db.String(),unique = True)
    rfm_hardware_specs_str = db.Column (db.String())
    rfm_provider_id = db.Column (db.Integer,db.ForeignKey ('rfmproviders.id'))
    rfm_provider_name = db.Column (db.String())
    rfm_compliance_level = db.Column (db.Integer)
    rfm_fw_ver_hash = db.Column (db.String())
    rfm_hw_uid = db.Column (db.String())

    def __init__ (self,rfm_name,rfm_unique_id,rfm_hardware_specs,rfm_provider_id,
            compliance_level,fw_ver_hash,hw_uid):
        self.rfm_name = rfm_name
        self.rfm_unique_id = rfm_unique_id
        self.rfm_hardware_specs_str = rfm_hardware_specs
        self.rfm_provider_id = rfm_provider_id

        rfm_provider = RegisteredFlightModuleProvider.query.filter_by (id = 
                rfm_provider_id).first()
        self.rfm_provider_name = rfm_provider.rfmp_name
        self.rfm_compliance_level = compliance_level
        rfm_fw_ver_hash = fw_ver_hash
        rfm_hw_uid = hw_uid

class GCSUser (db.Model):
    __tablename__ = 'gcsusers'
    id = db.Column (db.Integer,primary_key = True)
    username = db.Column (db.String(),unique = True)
    password = db.Column (db.String())
    salt = db.Column (db.String())
    firstname = db.Column (db.String())
    lastname = db.Column (db.String())
    email_id = db.Column (db.String())

    def __init__ (self,username,password,salt,firstname,lastname,email_id):
        self.username = username
        self.password = password
        self.salt = salt
        self.firstname = firstname
        self.lastname = lastname
        self.email_id = email_id

    def __repr__ (self):
        return '<id {}>'.format (self.id)

class Pilot (db.Model):
    __tablename__ = 'pilots'
    id =  db.Column (db.Integer,primary_key = True)
    gcsuser_id = db.Column (db.Integer,db.ForeignKey ('gcsusers.id'))
    pilot_fname = db.Column (db.String())
    pilot_lname = db.Column (db.String())
    pilot_gcsusername = db.Column (db.String())
    uaop = db.Column (db.String())
   
    def __init__ (self,gcsuser_id):
        self.gcsuser_id = gcsuser_id
        gcsuser = GCSUser.query.filter_by (id = gcsuser_id).first()
        self.pilot_fname = gcsuser.firstname
        self.pilot_lname = gcsuser.lastname
        self.pilot_gcsusername = gcsuser.username
        self.uaop = 'TBD'


class Drone (db.Model):
    __tablename__ = 'drones'
    id = db.Column (db.Integer,primary_key = True)
    unique_id_number = db.Column (db.String(),unique = True)
    drone_name = db.Column (db.String(), unique = True)
    model = db.Column (db.String())
    motor_count = db.Column (db.Integer)
    battery_type = db.Column (db.String())
    status  = db.Column (db.String())
    jobid_queue = db.Column (ARRAY (db.Integer))
    r_flight_module_id = db.Column (db.Integer,db.ForeignKey ('rfmodules.id'))
    rfm_name = db.Column (db.String())

    def __init__ (self,drone_name,model,motor_count,battery_type,rfm_id):
        self.drone_name = drone_name
        self.model = model
        self.motor_count = motor_count
        self.battery_type = battery_type
        self.status = 'Available'
        self.r_flight_module_id = rfm_id
        rfm = RegisteredFlightModule.query.filter_by (id = rfm_id).first()
        self.rfm_name = rfm.rfm_name


    def assign_job (self,job_id):
        if job_id is None:
            print ("WHYYYY")
        print (job_id)
        if self.jobid_queue is None:
            newlist = list()
            newlist.append (job_id)
            self.jobid_queue = newlist
            flag_modified (self,'jobid_queue')
        else:
            newlist = list(self.jobid_queue)
            newlist.append (job_id)
            self.jobid_queue = newlist
            flag_modified (self,'jobid_queue')
        self.status = "Jobs in Queue"
    
    def disable (self):
        if self.jobid_queue is None:
            self.status = 'Disabled'
            return True
        else:
            return False

    def has_jobs_scheduled (self):
        return not self.jobid_queue is None

    def job_queue_int (self):
        return self.jobid_queue

    
class Payload (db.Model):
    __tablename__ = 'payloads'
    id = db.Column (db.Integer,primary_key = True)
    type_str = db.Column (db.String())
    item = db.Column (db.String())
    storage_type = db.Column (db.String())
    item_type = db.Column (db.String())
    weight = db.Column (db.Integer)
    uom = db.Column (db.String())
    stock = db.Column (db.Integer)
    value = db.Column (db.Float)

    def __init__ (self, type_str,item,storage_type,item_type,weight,uom,stock,value):
        self.type_str = type_str
        self.item = item
        self.storage_type = storage_type
        self.item_type = item_type
        self.weight = weight
        self.uom = uom
        self.stock = stock
        self.value = value


class Job (db.Model):
    __tablename__ = 'jobs'
    id = db.Column (db.Integer,primary_key = True)
    startDate = db.Column (db.DateTime)
    endDate = db.Column (db.DateTime)
    drone_id = db.Column (db.Integer, db.ForeignKey ('drones.id'))
    status = db.Column (db.String())
    geofence_lat = db.Column (ARRAY (db.Float))
    geofence_long = db.Column (ARRAY (db.Float))
    
    payload_id = db.Column (db.Integer, db.ForeignKey ('payloads.id'))
    payload_count = db.Column (db.Integer)
    payload_weight = db.Column (db.Integer)
    max_altitude_level_ft = db.Column (db.Float)
    deployment_purpose = db.Column (db.String())

    location_origin_lat = db.Column (db.Float)
    location_origin_lon = db.Column (db.Float)
    location_dest_lat = db.Column (db.Float)
    location_dest_lon = db.Column (db.Float)

    location_origin_str = db.Column (db.String())
    location_dest_str = db.Column (db.String())

    def __init__ (self, sdate, edate, drone_id, geofence_lat,
            geofence_long, payload_id,payload_stock, max_alt,
            origin_lat,origin_lon,dest_lat,dest_lon):
        self.startDate = sdate
        self.endDate = edate
        self.drone_id = drone_id
        self.payload_id = payload_id
        self.status = "PENDING APPROVAL"
        self.payload_count = payload_stock
       
        self.geofence_lat = geofence_lat
        self.geofence_long = geofence_long

        payload = Payload.query.filter_by (id = payload_id).first ()
        payload.stock -= self.payload_count
        db.session.commit ()

        self.payload_weight = payload.weight * payload_stock
        self.max_altitude_level_ft = max_alt
        self.deployment_purpose = 'TEST'

        self.location_origin_lat = origin_lat
        self.location_origin_lon = origin_lon
        self.location_dest_lat = dest_lat
        self.location_dest_lon = dest_lon

        latlng = [float (origin_lat),float (origin_lon)]
        g = geocoder.mapbox (latlng,method='reverse',key='pk.eyJ1IjoiY2Fub3BlZXJ1cyIsImEiOiJjandidGhuZDkwa2V2NDl0bDhvem0zcDMzIn0.g1NXF5VQiDwn66KAsr-_dw')
        if g.json is None:
            self.location_origin_str = "Unknown Location"
        else:
            self.location_origin_str = g.json['address']

        latlng = [float (dest_lat),float (dest_lon)]
        g = geocoder.mapbox (latlng,method='reverse',key='pk.eyJ1IjoiY2Fub3BlZXJ1cyIsImEiOiJjandidGhuZDkwa2V2NDl0bDhvem0zcDMzIn0.g1NXF5VQiDwn66KAsr-_dw')
        if g.json is None:
            self.location_dest_str = "Unknown Location"
        else:
            self.location_dest_str = g.json['address']
        drone_sel = Drone.query.filter_by (id = self.drone_id).first ()
        drone_sel.assign_job (self.id)
        db.session.commit ()


    def is_pending (self):
        return self.status == 'PENDING APPROVAL'

    def get_assigned_drone (self):
        drone_ins = Drone.query.filter_by (id = self.drone_id).first()
        return drone_ins

    def get_assigned_payload (self):
        payload = Payload.query.filter_by (id = self.payload_id).first ()
        return payload


class LogFile (db.Model):
    __tablename__ = 'logfiles'
    id = db.Column (db.Integer,primary_key = True)
    filename = db.Column (db.String(),unique = True)
    filesize = db.Column (db.Integer)
    upload_user_id = db.Column (db.Integer,db.ForeignKey ('gcsusers.id'))
    upload_username = db.Column (db.String())
    upload_timestamp = db.Column (db.DateTime)
    drone_related_id = db.Column (db.Integer,db.ForeignKey ('drones.id'))
    drone_related_name = db.Column (db.String())
    file_blog = db.Column (db.LargeBinary)

    def __init__ (self,filename,upload_user_id,drone_id,fsize,blob):
        self.filename = filename
        self.upload_user_id = upload_user_id
        self.upload_username = GCSUser.query.filter_by (id = upload_user_id).first ().username
        self.upload_timestamp = datetime.now()
        self.drone_related_id = drone_id
        self.drone_related_name = Drone.query.filter_by (id = drone_id).first ().drone_name 
        self.filesize = fsize
        self.file_blog = blob

class IncidentModAction (db.Model):
    __tablename__ = 'incidentmodactions'
    id = db.Column (db.Integer,primary_key = True)
    incident_id = db.Column (db.Integer,db.ForeignKey ('incidents.id'))
    user_id = db.Column (db.Integer,db.ForeignKey ('gcsusers.id'))
    m_type = db.Column (db.String())
    incident_pre_status = db.Column (db.String())
    incident_post_status = db.Column (db.String())
    date_timestamp = db.Column (db.DateTime)


    def __init__ (self,m_type,user_id,incident_id):
        self.m_type = m_type
        self.user_id = user_id
        self.incident_id = incident_id

        if self.m_type == 'Resolution':
            incident_post_status = 'Resolved'
        elif self.m_type == 'Creation':
            incident_pre_status = 'NA'
            incident_post_status = 'Queued'

        date_timestamp = datetime.now()


            
        
class Incident (db.Model):
    __tablename__ = 'incidents'
    id = db.Column (db.Integer,primary_key = True)
    title = db.Column (db.String())
    description = db.Column (db.String())
    user_issuedId = db.Column (db.Integer,db.ForeignKey ('gcsusers.id'))
    user_issuedName = db.Column (db.String())
    drone_relatedId = db.Column (db.Integer,db.ForeignKey('drones.id'))
    drone_relatedName = db.Column (db.String())
    status = db.Column (db.String())
    date_created = db.Column (db.DateTime)
    priority = db.Column (db.String())

    def __init__ (self,title,description,user_issued,username,drone_relatedId,drone_relatedName,priority):
        self.title = title
        self.description = description
        self.user_issuedId = user_issued
        self.user_issuedName = username
        self.drone_relatedId = drone_relatedId
        self.drone_relatedName = drone_relatedName
        self.status = 'Pending Action'
        self.date_created = datetime.now()
        self.priority = priority
class CustomerUser (db.Model):
    __tablename__ = 'customers'
    id = db.Column (db.Integer,primary_key = True)
    username = db.Column (db.String())
    firstname = db.Column (db.String())
    lastname = db.Column (db.String())
    emailid = db.Column (db.String())
    phoneno = db.Column (db.String())
    default_address_str1 = db.Column (db.String())
