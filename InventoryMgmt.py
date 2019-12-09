from flask import render_template,redirect,url_for,send_from_directory
from models import Payload,Drone,Job
import FMSGeneric as fmg

ALLOWED_BATCH_INVENTORY_TYPES = ['csv','CSV']

def listAllInventory (session,request):
    if fmg.isValidSession (session):
        payloads = Payload.query.all ()
        return render_template ('inventory/index.html',inventory = payloads,
                count = len (payloads))
    else:
        return redirect ('/gcslogin',code = 302)

def newInventoryPage (session,request):
    if fmg.isValidSession (session):
        return render_template ('inventory/newinventory.html')
    else:
        return redirect ('/gcslogin',code = 302)


def newInventoryAction (session,request,db):
    if fmg.isValidSession (session) and request.method == 'POST':
        type_str = request.form ['type']
        item = request.form ['item']
        storage_type = request.form ['storageType']
        item_type = request.form ['itemType']
        item_weight = request.form ['weight']
        uom = request.form ['uom']
        stock = request.form ['stock']
        value = request.form ['value']

        payload = Payload (type_str,item,storage_type,
                item_type,item_weight,uom,stock,value)
        db.session.add (payload)
        db.session.commit ()
        return redirect ('/inventory',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)

def batchInventoryUploadPage (session,request):
    if fmg.isValidSession (session):
        return render_template ('inventory/batchinventory_upload.html')
    else:
        return redirect ('/gcslogin',code = 302)

def checkCSVAllowedFile (filename):
    return '.' in filename and \
            filename.rsplit ('.',1)[1].lower () in ALLOWED_BATCH_INVENTORY_TYPES

def inventoryEditPage (session,request):
    if fmg.isValidSession (session):
        return "Work in progress"
    else:
        return redirect ('/gcslogin',code = 302)

