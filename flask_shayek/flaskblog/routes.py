import os
from uuid import uuid4
from flask import current_app as app
from flask import render_template, url_for, flash, redirect, request, Flask, session, jsonify, abort
from flaskblog import app, firebase, login_manager
from flaskblog.forms import RegistrationForm, LoginForm, RegistrationRequestForm
from flask_login import login_user, current_user, logout_user, login_required, UserMixin
import firebase_admin
from firebase_admin import credentials, db, firestore, storage, auth
from werkzeug.utils import secure_filename
import random
import string

# Firebase Admin SDK Initialization
cred = credentials.Certificate('C:/Users/huaweii/Downloads/shayek-560ec-firebase-adminsdk-b0vzc-d1533cb95f.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://shayek-560ec-default-rtdb.firebaseio.com/',
    'storageBucket': 'shayek-560ec.appspot.com'
})

posts = [
    {
        'author': 'صحيفة مكة',
        'title': 'الأميرة ساره بنت مساعد تكرم الفائزات بجائزة سيدة الباحة',
        'content': 'رعت صاحبة السمو الملكي الأميرة سارة بنت مساعد بن عبدالعزيز حرم سمو أمير منطقة الباحة، بمركز الحسام للمعارض والمؤتمرات، حفل تكريم الفائزات بجائزة “سيدة الباحة” في نسختها الأولى والتي تعد إحدى مبادرات فرع وزارة الموارد البشرية والتنمية الاجتماعية بمنطقة الباحة لتمكين المرأة والإحتفاء بالسيدات المتميزات.',
        'date_posted': 'Mar 20, 2024'

    },
    {
        'author': 'جريدة الرياض',
        'title': 'مجلس الوزراء: 27 من مارس يوماً رسمياً لـ السعودية الخضراء',
        'content': 'رأس خادم الحرمين الشريفين الملك سلمان بن عبدالعزيز آل سعود ـ حفظه الله ـ، الجلسة التي عقدها مجلس الوزراء، الثلاثاء، في جدة.',
        'date_posted': 'Mar 20, 2024'

    }
]

@app.route('/')
@app.route('/homepage')
def home():
    return render_template('home.html', posts=posts)


@app.route('/about')
def about():
    return render_template('about.html', title = 'من نحن؟')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash(f'تم تسجيل حساب باسم {form.username.data}!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', title='استمارة التسجيل', form=form)

import requests
from flask import jsonify

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        api_key = "AIzaSyAXgzwyWNcfI-QSO_IbBVx9luHc9zOUzeY"
        request_payload = {
            "email": form.email.data,
            "password": form.password.data,
            "returnSecureToken": True
        }
        try:
            response = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}", json=request_payload)
            response.raise_for_status() 
            user_data = response.json()
            session['logged_in'] = True
            session['role'] = 'user'
            flash('تم تسجيل دخولك بنجاح', 'success')
            return redirect(url_for('home'))
        except requests.exceptions.HTTPError as e:
            error_json = e.response.json()
            error_message = error_json.get('error', {}).get('message', 'UNKNOWN_ERROR')
            flash(f'فشل تسجيل دخولك، راجع بريدك الإلكتروني وكلمة المرور. Error: {error_message}', 'danger')
            pass
    return render_template('login.html', title='تسجيل الدخول', form=form)

def upload_file_to_firebase_storage(file):
    if file:
        filename = secure_filename(file.filename)
        bucket = storage.bucket()
        blob = bucket.blob(f"company_docs/{filename}")
        blob.upload_from_string(file.read(), content_type=file.content_type)
        blob.make_public()
        return f"gs://shayek-560ec.appspot.com/company_docs/{filename}"


@app.route('/register_request', methods=['GET', 'POST'])
def register_request():
    form = RegistrationRequestForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        company_name = form.company_name.data
        company_docs = request.files.get('company_docs')
        file_url = upload_file_to_firebase_storage(company_docs)

        registration_data = {
            'username': username,
            'email': email,
            'company_name': company_name,
            'company_docs_url': file_url,
            'status' : 'under review'
        }

        db.reference('registration_requests').push(registration_data)

        flash('تم رفع طلبكم بنجاح', 'success')
        return redirect(url_for('home'))
    else:
        return render_template('register_request.html', title='طلب تسجيل حساب', form=form)


@app.route('/shayekModel')
def shayekModel():
    return render_template('shayekModel.html', title = 'نشيّك؟')



@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return User(user_id)
    return None

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id
        self.is_admin = True if user_id == 'admin' else False 


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'adminpass':
            user = User('admin')  
            login_user(user)
            session['logged_in'] = True
            session['role'] = 'admin'
            flash('تم تسجيل دخولك بنجاح', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('فشل تسجيل دخولك، راجع بريدك الإلكتروني وكلمة المرور.')
    return render_template('admin_login.html')


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(401) 
    ref = db.reference('registration_requests')
    requests = ref.order_by_child('status').equal_to('under review').get()
    
    for request in requests.values():
        if 'company_docs_url' in request:
            gs_url = request['company_docs_url']
            if gs_url.startswith('gs://'):
                https_url = gs_url.replace('gs://', 'https://storage.googleapis.com/')
                request['company_docs_url'] = https_url
    
    return render_template('admin_dashboard.html', requests=requests)



from flask import redirect, url_for, request

@app.route('/verify_request/<request_id>', methods=['POST'])
@login_required
def verify_request(request_id):
    ref_request = db.reference(f'registration_requests/{request_id}')
    request_data = ref_request.get()
    if request_data:
        if 'decline' in request.form:
            ref_request.update({'status': 'declined'})  
            return redirect(url_for('admin_dashboard'))
       
        try:
            user_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            new_user = auth.create_user(
                email=request_data['email'],
                password=user_password,
            )
            user_data ={
            'username': request_data['username'],
            'email': request_data['email'],
            'password': user_password,
            'posts': {} }
            
            ref_user = db.reference('users').push(user_data)
            
            ref_request.update({'status': 'accepted', 'uid': new_user.uid})
            
            flash('تم قبول طلب التسجيل وإنشاء الحساب', 'success')
            js_script = f"alert('{user_password} هو: {request_data['email']} الرقم السري للحساب ');"
            return f"<script>{js_script}</script><script>window.location.href = '{url_for('admin_dashboard')}';</script>"
        
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'danger')
            return redirect(url_for('admin_dashboard'))

        return redirect(url_for('admin_dashboard'))
    else:
        flash('Request data not found.', 'danger')
        return redirect(url_for('admin_dashboard'))


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('role', None)
    flash('تم تسجيل خروجك بنجاح', 'success')
    return redirect(url_for('home'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('role', None)
    flash('تم تسجيل خروجك بنجاح', 'success')
    return redirect(url_for('admin_login'))
