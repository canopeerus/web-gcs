from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy ()

class GCSUser (db.Model):
    __tablename__ = 'gcsusers'
    id = db.Column (db.Integer,primary_key = True)
    username = db.Column (db.String(),unique = True)
    password = db.Column (db.String())
    salt = db.Column (db.String())

    def __init__ (self,username,password,salt):
        self.username = username
        self.password = password
        self.salt = salt

    def __repr__ (self):
        return '<id {}>'.format (self.id)

