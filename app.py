#!/usr/bin/env python3
from flask import Flask
import os
app = Flask (__name__)

@app.route ('/')
def homepage ():
    return "Redwing homepage placeholder"

if __name__ == "__main__":
    app.secret_key = os.urandom (12)
    app.run (debug = True)
