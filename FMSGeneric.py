from models import GCSUser
from authutils import verify_password,hash_password
from flask import render_template,redirect,url_for,send_from_directory

def isValidSession (session) -> bool:
    return 'gcs_user' in session and session ['gcs_logged_in']

def gcsLoginPage (session,request):
    if not isValidSession (session):
        if 'redirect' in request.args:
            redirect = 1
        else:
            redirect = 0

        if 'error' in request.args:
            return render_template ('fmsgeneric/gcs_login.html',redirect = str (redirect),result = 'error')
        else:
            return render_template ('fmsgeneric/gcs_login.html', redirect = str (redirect))
    else:
        return redirect ('/gcsportal',code = 302)

def gcsLoginAction (session,request):
    if not request.method == 'POST':
        return redirect ('/gcslogin',code = 302)

    usernameval = request.form ['username']
    pwval = request.form ['password']
    qresult = GCSUser.query.filter_by (username = usernameval).first ()
    if qresult is None:
        return redirect ('/gcslogin?error')
    
    qpassword = qresult.password
    qsalt = qresult.salt

    if verify_password (qpassword,pwval,qsalt):
        session ['gcs_logged_in'] = True
        session ['gcs_user'] = usernameval
        session.modified = True
        print (request.form.get ('redirect'))
        if request.form.get ('redirect') == '1':
            if 'src_url' in session:
                return redirect (session ['src_url'])
            else:
                return redirect ('/gcsportal')
        else:
            return redirect ('/gcsportal')
    else:
        return redirect ('/gcslogin?error')

def showUserProfile (session,request):
    if isValidSession (session):
        updated = 0
        if 'updated' in request.args:
            updated = 1

        user = session ['gcs_user']
        qresult = GCSUser.query.filter_by (username = user).first ()
        return render_template ('fmsgeneric/gcsprofile.html',
                username = qresult.username, firstname = qresult.firstname,
                lastname = qresult.lastname, email_id = qresult.email_id,
                updated = updated)
    else:
        session ['src_url'] = '/gcsuserprofile'
        return redirect ('/gcslogin?redirect',code = 302)

def profileEditAction (session,request,db):
    if isValidSession (session) and request.method == 'POST':
        user_instance = GCSUser.query.filter_by (username = user).first ()
        if 'firstname_update' in request.form:
            n_fname = request.form['firstname_update']
            user_instance.firstname = n_fname
        
        if 'lastname_update' in request.form:
            n_lname = request.form ['lastname_update']
            user_instance.lastname = n_lname

        if 'email_update' in request.form:
            n_email = request.form ['email_update']
            user_instance.email_id = n_email

        db.session.commit ()
        return redirect ('/gcsuserprofile?updated',code = 302)
    else:
        return redirect ('/gcslogin',code = 302)

def gcsUserUpdatePasswordPage (session,request):
    if isValidSession (session):
        err = False
        if 'error' in request.args:
            err = True
        if err:
            return render_template ('fmsgeneric/changepassword.html',result = 'error',
                    username = session ['gcs_user'])
        else:
            return render_template ('fmsgeneric/changepassword.html',
                    username = session ['gcs_user'])
    else:
        session ['src_url'] = '/updatepassword'
        return redirect ('/gcslogin?redirect')

def gcsUserUpdatePasswordAction (session,request,db):
    if isValidSession (session) and request.method == 'POST':
        gcsuser = GCSUser.query.filter_by (username = session['gcs_user']).first ()
        gsalt = gcsuser.salt
        oldpas = hash_password (request.form ['old_password'],gsalt)
        if oldpas == gcsuser.password:
            newpas = hash_password (request.form ['password'],gsalt)
            gcsuser.password = newpas
            db.session.commit ()
            return redirect ('/gcsuserprofile',code = 302)
        else:
            return redirect ('/updatepassword?error',code = 302)
    else:
        return redirect ('/gcslogin', code = 302)


def gcsLogout (session,request):
    if isValidSession (session):
        del session ['gcs_user']
        if 'src_url' in session:
            del session ['src_url']
        session ['gcs_logged_in'] = False

    return redirect ('/',code = 302)

def gcsSignupPage (session,request):
    return render_template ('fmsgeneric/gcs_signup.html')

def gcsSignupAction (session,request,db):
    if request.method == 'POST':
        salt = uuid.uuid4().hex
        pwd_hash = hash_password (request.form ['password'].strip(),salt)

        match = GCSUser.query.filter_by (username = request.form ['username']).first ()
        if match is None:
            username = request.form ['username'].strip ()
            firstname = request.form ['firstname'].strip ()
            lastname = request.form ['lastname'].strip ()
            email_id = request.form ['email_id'].strip ()

            gcsuser_instance = GCSUser (username,pwd_hash,salt,firstname,lastname,
                    email_id)
            db.session.add (gcsuser_instance)
            db.session.commit ()
        return redirect ('/gcsportal')
    else:
        return redirect ('/gcslogin')

def gcsHome (session,request):
    if isValidSession (session):
        return redirect ('/jobtracker',code = 302)
    else:
        session ['url_src'] = '/gcsportal'
        return redirect ('/gcslogin?redirect',code = 302)
