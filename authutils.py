import os,hashlib,uuid

def hash_password (password,salt):
    hashv = hashlib.sha512()
    hashv.update (( '%s%s' % (salt,password)).encode('utf-8'))
    pwhash = hashv.hexdigest ()
    return  pwhash

def verify_password (stored_password,provided_password,salt):
    provided_hash = hash_password (provided_password,salt)
    return provided_hash == stored_password
