#!/usr/bin/env python3
from flask import Flask,render_template,redirect,session,abort,request,flash
import os
app = Flask (__name__)
app.secret_key = os.urandom (24)
@app.route ('/')
def homepage ():
    return render_template("index.html")
    
    
# Main GCS Page route, redirects to 'gcslogin' if not logged in
@app.route ("/gcsportal",methods=['GET','POST'])
def gcshome():
    if not session.get ('gcs_logged_in'):
        return redirect("/gcslogin",code=302)
    else:
        return render_template("gcshome.html")

# GCS Login page route
@app.route ("/gcslogin")
def gcslogin ():
    if not session.get ('gcs_logged_in'):
        return render_template ("gcs_login.html")


# GCS Login form action route, accepts only POST requests
@app.route ("/gcsloginform",methods=['POST'])
def gcsloginaction ():
    session['gcs_logged_in'] = True
    return redirect("/gcsportal",code=302)

if __name__ == "__main__":
    app.run (debug = True)
