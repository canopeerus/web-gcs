# Describes models for various entities in the GCS

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from queue import Queue

db = SQLAlchemy ()

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

class Drone (db.Model):
    __tablename__ = 'drones'
    id = db.Column (db.Integer,primary_key = True)
    drone_name = db.Column (db.String(), unique = True)
    model = db.Column (db.String())
    motor_count = db.Column (db.Integer)
    battery_type = db.Column (db.String())
    status  = db.Column (db.String())
    jobid_queue = db.Column (db.String())

    def __init__ (self,drone_name,model,motor_count,battery_type):
        self.drone_name = drone_name
        self.model = model
        self.motor_count = motor_count
        self.battery_type = battery_type
        self.status = 'Available'

    def assign_job (self,job_id):
        if self.jobid_queue is None:
            self.jobid_queue = str(job_id)
        else:
            self.jobid_queue += "-"+str(job_id)
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
        str_arr = self.jobid_queue.split ('-')
        for i in range (len (str_arr)):
            str_arr[i] = int (str_arr[i])
        return str_arr

    
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
    date = db.Column (db.DateTime)
    drone_id = db.Column (db.Integer, db.ForeignKey ('drones.id'))
    status = db.Column (db.String())
    location_origin_lat = db.Column (db.String())
    location_origin_long = db.Column (db.String())
    location_dest_lat = db.Column (db.String())
    location_dest_long = db.Column (db.String())
    location_dest_string = db.Column (db.String())
    location_origin_string = db.Column (db.String())
    payload_id = db.Column (db.Integer, db.ForeignKey ('payloads.id'))
    payload_count = db.Column (db.Integer)
    payload_weight = db.Column (db.Integer)

    def __init__ (self, date, drone_id, location_origin_lat,
            location_origin_long, location_dest_lat, location_dest_long,
            location_dest_string,payload_id,payload_stock,location_origin_string):
        self.date = date
        self.drone_id = drone_id
        self.location_origin_lat = location_origin_lat
        self.location_origin_long = location_origin_long
        self.location_dest_lat = location_dest_lat
        self.location_dest_long = location_dest_long
        self.payload_id = payload_id
        self.location_dest_string = location_dest_string
        self.location_origin_string = location_origin_string
        self.status = "PENDING APPROVAL"
        self.payload_count = payload_stock
        
        payload = Payload.query.filter_by (id = payload_id).first ()
        payload.stock -= self.payload_count
        db.session.commit ()

        self.payload_weight = payload.weight * payload_stock
        self.location_origin_string = location_origin_string

    def is_pending (self):
        return self.status == 'PENDING APPROVAL'

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

    def __init__ (self,filename,upload_user_id,upload_username,drone_id,
            drone_name,fsize):
        self.filename = filename
        self.upload_user_id = upload_user_id
        self.upload_username = upload_username
        self.upload_timestamp = datetime.now()
        self.drone_related_id = drone_id
        self.drone_related_name = drone_name
        self.filesize = fsize

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
