# Describes models for various entities in the GCS

from flask_sqlalchemy import SQLAlchemy
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

