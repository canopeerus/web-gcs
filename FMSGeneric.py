from models import GCSUser
from flask import render_template,redirect,url_for,send_from_directory

def isValidSession (session) -> bool:
    return 'gcs_user' in session and session ['gcs_logged_in']
