# Describes models for various entities in the GCS

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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

    def __init__ (self,drone_name,model,motor_count,battery_type):
        self.drone_name = drone_name
        self.model = model
        self.motor_count = motor_count
        self.battery_type = battery_type

class Payload (db.Model):
    __tablename__ = 'payloads'
    id = db.Column (db.Integer,primary_key = True)
    name = db.Column (db.String())
    weight = db.Column (db.Float)

    def __init__ (self, name, weight):
        self.name = name
        self.weight = weight


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
    payload_id = db.Column (db.Integer, db.ForeignKey ('payloads.id'))

    def __init__ (self, date, drone_id, status, location_origin_lat,
            location_origin_long, location_dest_lat, location_dest_long, payload_id):
        self.date = date
        self.drone_id = drone_id
        self.status = status
        self.location_origin_lat = location_origin_lat
        self.location_origin_long = location_origin_long
        self.location_dest_lat = location_dest_lat
        self.location_dest_long = location_dest_long
        self.payload_id = payload_id
    
