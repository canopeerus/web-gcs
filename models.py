from app import db

class GCSUser (db.Model):
    __tablename__ = 'gcsusers'
    id = db.Column (db.Integer, primary_key = True)
    username = db.Column (db.String())
    password = db.Column (db.String())

    def __init__ (self, username, password):
        self.username = username
        self.password = password

    def __repr__ (self):
        return '<id {}>'.format (self.id)

    def serialize (self):
        return {
                'id':self.id,
                'username':self.username,
                'password':self.password
                }
