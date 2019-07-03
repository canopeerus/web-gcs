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
    name = db.Column (db.String())
    weight = db.Column (db.Float)
    stock = db.Column (db.Integer)

    def __init__ (self, name, weight, stock):
        self.name = name
        self.weight = weight
        self.stock = stock


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
