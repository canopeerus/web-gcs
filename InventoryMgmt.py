from flask import render_template,redirect,url_for,send_from_directory
from models import Payload,Drone,Job
import FMSGeneric as fmg
import pandas as pd
from collections import Counter

ALLOWED_BATCH_INVENTORY_TYPES = ['csv','CSV']
ACCEPTABLE_COLUMNS = ['type','item','storage_type','item_type','weight',
        'uom','stock','value']

def listAllInventory (session,request):
    if fmg.isValidSession (session):
        payloads = Payload.query.all ()
        return render_template ('inventory/index.html',inventory = payloads,
                count = len (payloads),username = session ['gcs_user'])
    else:
        session ['src_url'] = '/inventory'
        return redirect ('/gcslogin?redirect')

def newInventoryPage (session,request):
    if fmg.isValidSession (session):
        return render_template ('inventory/newinventory.html',
                username = session ['gcs_user'])
    else:
        session ['src_redirect'] = '/addinventory'
        return redirect ('/gcslogin?redirect')


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
        return render_template ('inventory/batchinventory_upload.html',
                username = session ['gcs_user'])
    else:
        session ['src_url'] = '/batchinventoryupload'
        return redirect ('/gcslogin?redirect')

def checkCSVAllowedFile (filename):
    return '.' in filename and \
            filename.rsplit ('.',1)[1].lower () in ALLOWED_BATCH_INVENTORY_TYPES

def inventoryEditPage (session,request):
    if fmg.isValidSession (session):
        return "Work in progress"
    else:
        session ['src_url'] = '/inventory'
        return redirect ('/gcslogin?redirect')

def batchInventoryAction (session,request,db):
    if fmg.isValidSession (session) and request.method == 'POST':
        if not 'file' in request.files:
            return 'error:no file'
        inputfile = request.files.get ('file')
        if inputfile is None:
            return "ERror!"
        if checkCSVAllowedFile (inputfile.filename):
            inputfile.save (inputfile.filename)
            df = pd.read_table (inputfile.filename,sep = ',')
            read_columns = list (df.columns.values)
            if Counter (read_columns) == Counter (ACCEPTABLE_COLUMNS):
                for index,row in df.iterrows ():
                    inventory_item = Payload (row ['type'],row['item'],
                        row['storage_type'],int (row['weight']),row['uom'],
                        int(row['stock']),float(row['value']))
                    db.session.add (inventory_item)
                db.session.commit ()
                os.remove (inputfile.filename)
            else:
                return "Invalid CSV Format"
            return redirect ('/inventory')
        else:
            return "Invalid File FOrmat"
    else:
        return redirect ('/gcslogin')
            
