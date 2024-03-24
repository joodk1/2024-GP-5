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
cred = credentials.Certificate('c:/Users/huaweii/downloads/shayek-560ec-firebase-adminsdk-b0vzc-d1533cb95f.json')
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


@app.route('/user/home')
def user_home():
    user_info = session.get('user_info')
    if user_info:      
        return render_template('user_home.html', posts=posts, user_info=user_info)
    else:
        flash('<i class="fas fa-times-circle me-3"></i> يرجى تسجيل الدخول أولاً', 'danger')
        return redirect(url_for('login'))


@app.route('/about')
def about():
    return render_template('about.html', title = 'من نحن؟')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash(f'<i class="fas fa-check-circle me-3"></i> تم تسجيل حساب باسم {form.username.data}!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', title='استمارة التسجيل', form=form)

import requests
from flask import jsonify
import os

def determine_user_role(email):
    users_ref = db.reference('users')
    users_query_result = users_ref.order_by_child('email').equal_to(email).get()
    if users_query_result:
        return 'user'
    admins_ref = db.reference('admins')
    admins_query_result = admins_ref.order_by_child('email').equal_to(email).get()
    if admins_query_result:
        return 'admin'
    return None  

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        api_key = "AIzaSyAXgzwyWNcfI-QSO_IbBVx9luHc9zOUzeY"
        request_payload = {
            "email": form.email.data,
            "password": form.password.data,
            "returnSecureToken": True
        }
        try:
            response = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}", json=request_payload)
            response.raise_for_status()
            user_info = response.json()
            email = form.email.data
            user_role = determine_user_role(email)
            session['logged_in'] = True
            session['role'] = user_role  # Set role based on user_role
            if user_role == 'user':
                username = fetch_username_from_database(email)
                session['user_info'] = {'email': email, 'username': username}
                flash('<i class="fas fa-check-circle me-3"></i> تم تسجيل دخولك بنجاح', 'success')
                return redirect(url_for('user_home'))
            elif user_role == 'admin':
                flash('<i class="fas fa-check-circle me-3"></i> تم تسجيل دخولك كمسؤول', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('<i class="fas fa-times-circle me-3"></i> راجع بريدك الإلكتروني وكلمة المرور.', 'danger')

        except requests.exceptions.HTTPError as e:
            error_json = e.response.json()
            error_message = error_json.get('error', {}).get('message', 'UNKNOWN_ERROR')
            flash(f'<i class="fas fa-times-circle me-3"></i> فشل تسجيل دخولك، راجع بريدك الإلكتروني وكلمة المرور. Error: {error_message}', 'danger')
    return render_template('login.html', title='تسجيل الدخول', form=form)

def fetch_username_from_database(email):
    user_ref = db.reference('users').order_by_child('email').equal_to(email).get()
    if user_ref:
        user_data = next(iter(user_ref.values()))
        return user_data.get('username', None)
    else:
        return None

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

        flash('<i class="fas fa-check-circle me-3"></i> تم رفع طلبكم بنجاح', 'success')
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

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'logged_in' in session and session['role'] == 'admin':
        ref = db.reference('registration_requests')
        requests = ref.order_by_child('status').equal_to('under review').get()

        for key, request in requests.items():
            if 'company_docs_url' in request and request['company_docs_url'].startswith('gs://'):
                gs_url = request['company_docs_url']
                https_url = gs_url.replace('gs://', 'https://storage.googleapis.com/', 1)
                request['company_docs_url'] = https_url
        
        return render_template('admin_dashboard.html', requests=requests)
    else:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح، الرجاء تسجيل الدخول كمسؤول', 'danger')
        return redirect(url_for('login'))


from flask import redirect, url_for, request
    
@app.route('/verify_request/<request_id>', methods=['POST'])
def verify_request(request_id):
    if 'logged_in' in session and session['role'] == 'admin':
        ref_request = db.reference(f'registration_requests/{request_id}')
        request_data = ref_request.get()

        if request_data:
            if 'decline' in request.form:
                ref_request.update({'status': 'declined'})
                flash('<i class="fas fa-check-circle me-3"></i> تم رفض الطلب بنجاح', 'info')
            else:
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
                    flash('<i class="fas fa-check-circle me-3"></i> تم قبول طلب التسجيل وإنشاء الحساب', 'success')
                    js_script = f"alert('{user_password} هو: {request_data['email']} الرقم السري للحساب ');"
                    return f"<script>{js_script}</script><script>window.location.href = '{url_for('admin_dashboard')}';</script>"
                except Exception as e:
                    flash(f'<i class="fas fa-times-circle me-3"></i> Error handling the request: {str(e)}', 'danger')
                    user_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

            return redirect(url_for('admin_dashboard'))
        else:
            flash('<i class="fas fa-times-circle me-3"></i> Request data not found.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('login'))



@app.route('/admin/logout')
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('role', None)
    session.pop('user_info', None) 
    flash('<i class="fas fa-check-circle me-3"></i> تم تسجيل خروجك بنجاح', 'success')
    return redirect(url_for('home'))
