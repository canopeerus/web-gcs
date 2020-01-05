from datetime import datetime
from lxml import etree
from signxml import XMLVerifier
from base64 import b64decode

def dateTimeMerge (date_str,time_str):
    return datetime.strptime (date_str + ' ' + time_str,'%Y-%m-%d %I:%M %p')

def getCoordsFloatList (coords_str):
    return list (map (float, coords_str.split(',')))

def verifyXMLSignature (file_obj):
    afile = open (file_obj,'rb')
    cert = etree.parse (afile).find ("X509Certificate").text
    assertion_data = XMLVerifier ().verify (b64decode (assertion_body),
        x509_cert = cert).signed_xml
    print (assertion_data)
