import os
from uuid import uuid4
from flask import current_app as app
from flask import render_template, url_for, flash, redirect, request, Flask, session, jsonify, abort
from flaskblog import app, firebase, login_manager
from flaskblog.forms import LoginForm, RegistrationRequestForm, UserLoginForm, UserRegistrationForm
from flask_login import login_user, current_user, logout_user, login_required, UserMixin
from flask_mail import Mail, Message
import firebase_admin
from firebase_admin import credentials, db, firestore, storage, auth
from werkzeug.utils import secure_filename
from datetime import datetime
import random
import string
import requests
import cv2
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model # type: ignore
import dlib
from werkzeug.security import generate_password_hash, check_password_hash

# Firebase Admin SDK Initialization
cred = credentials.Certificate(r'C:\Users\huaweii\Downloads\shayek-560ec-firebase-adminsdk-b0vzc-d1533cb95f.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://shayek-560ec-default-rtdb.firebaseio.com/',
    'storageBucket': 'shayek-560ec.appspot.com'
})
firebase_database = db.reference()

# Initializing the face detector
detector = dlib.get_frontal_face_detector()

# Loading the pre-trained model
model_path = r'C:\Users\huaweii\OneDrive\Documents\GitHub\2024-GP-5\flask_shayek\ResNet50_Model_Web.h5'
model = load_model(model_path)

def fetch_posts():
    posts_ref = db.reference('posts').order_by_child('timestamp')
    posts_snapshot = posts_ref.get()
    reversed_posts = {post_id: posts_snapshot[post_id] for post_id in reversed(list(posts_snapshot.keys()))}
    posts = []
    for post_id, post_data in reversed_posts.items():
        posts.append({
            'post_id': post_id,
            'author': post_data.get('author'),
            'author_email': post_data.get('author_email'),
            'timestamp': post_data.get('timestamp'),
            'title': post_data.get('title'),
            'content': post_data.get('body'),
            'media': post_data.get('media_url')
        })
    return posts

posts = fetch_posts()

@app.route('/')
@app.route('/homepage')
def homepage():
    posts = fetch_posts()
    return render_template('homepage.html', posts=posts)

@app.route('/NewsOutlet/home')
@login_required
def user_home():
    user_id = session.get('user_email')
    if user_id:
        user = load_user(user_id)
        if user:
            login_user(user)
            posts = fetch_posts()
            return render_template('newsoutlet_home.html', posts=posts, user=user, user_id=user_id)
        else:
            flash('<i class="fas fa-times-circle me-3"></i> يرجى تسجيل الدخول أولاً', 'danger')
            return redirect(url_for('/NewsOutlet/login'))
    else:
        flash('<i class="fas fa-times-circle me-3"></i> يرجى تسجيل الدخول أولاً', 'danger')
        return redirect(url_for('/NewsOutlet/login'))

@app.route('/NewsOutlet/profile')
def profile():
    user_email = current_user.get_id()
    if not user_email:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('/NewsOutlet/login'))

    user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(user_email).get()
    if not user_ref:
        flash('<i class="fas fa-times-circle me-3"></i> المستخدم غير موجود', 'danger')
        return redirect(url_for('/NewsOutlet/login'))
    username = list(user_ref.values())[0].get('username')
    posts = fetch_posts()
    return render_template('newsoutlet_profile.html', user_info=username, posts=posts)

def fetch_posts_by_user(user_email):
    posts_ref = db.reference('posts').order_by_child('author_email').equal_to(user_email)
    posts_snapshot = posts_ref.get()
    if not posts_snapshot:
        return []

    reversed_posts = {post_id: posts_snapshot[post_id] for post_id in reversed(list(posts_snapshot.keys()))}
    posts = []
    for post_id, post_data in reversed_posts.items():
        posts.append({
            'post_id': post_id,
            'author': post_data.get('author'),
            'author_email': post_data.get('author_email'),
            'timestamp': post_data.get('timestamp'),
            'title': post_data.get('title'),
            'content': post_data.get('body'),
            'media': post_data.get('media_url')
        })
    return posts

@app.route('/profile/<username>')
@login_required
def user_profile(username):
    user = None
    newsoutlet_ref = firebase_database.child('newsoutlet')
    newsoutlet_data = newsoutlet_ref.get()
    if newsoutlet_data:
        for uid, userdata in newsoutlet_data.items():
            if userdata.get('username') == username:
                user = {'id': userdata.get('id'), 'username': userdata.get('username'), 'email': userdata.get('email')}
                break
    
    if user:
        posts = fetch_posts_by_user(user['email'])
        return render_template('newsoutlet_myprofile.html', user=user, posts=posts)
    else:
        flash('لم نستطع إيجاد الحساب.', 'danger')
        return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html', title = 'من نحن؟')

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

@app.route('/NewsOutlet/login', methods=['GET', 'POST'])
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
            user_email= user_info['email']
            user_id= user_info['localId']
            if user_email:
                user = load_user(user_email) 
                if user:
                    login_user(user)  
                    session['user_email'] = user_info['email']
                    session['logged_in'] = True
                    flash('<i class="fas fa-check-circle me-3"></i> تم تسجيل دخولك بنجاح', 'success')
                    return redirect(url_for('/NewsOutlet/home'))
                else:
                    flash('<i class="fas fa-times-circle me-3"></i> الحساب غير موجود.', 'danger')
            else:
                flash('<i class="fas fa-times-circle me-3"></i> الحساب غير موجود.', 'danger')
        except requests.exceptions.HTTPError as e:
            try:
                error_json = e.response.json()
                error_message = error_json.get('error', {}).get('message', 'مشكلة غير معروفة')
            except ValueError:
                error_message = "حدثت مشكلة أثناء المعالجة، فضلًا حاول مجددًا."
            flash(f'<i class="fas fa-times-circle me-3"></i> {error_message}', 'danger')
        except ValueError:
            flash('<i class="fas fa-times-circle me-3"></i> حدثت مشكلة أثناء المعالجة، فضلًا حاول مجددًا.', 'danger')

    return render_template('newsoutlet_login.html', title='تسجيل الدخول', form=form)

@app.route('/Member/login', methods=['GET', 'POST'])
def member_login():
    form = UserLoginForm()
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
            
            user_email = user_info['email']
            user_id = user_info['localId']
            user_data = db.reference(f'users/{user_id}').get()  
            
            if user_email:
                user = load_user(user_email)
                if user:
                    login_user(user)  
                    is_newsoutlet = user_data.get('is_newsoutlet', False)
                    session['user_email'] = user_info['email']
                    session['logged_in'] = True
                     
                    return redirect(url_for('member_home'))  
                else:
                    flash('<i class="fas fa-times-circle me-3"></i> الحساب غير موجود.', 'danger')
            else:
                flash('<i class="fas fa-times-circle me-3"></i> الحساب غير موجود.', 'danger')
            user_data = db.reference(f'newsoutlets/{user_id}').get() 

        except requests.exceptions.HTTPError as e:
            flash('<i class="fas fa-times-circle me-3"></i> حدث خطأ أثناء تسجيل الدخول.', 'danger')
        
    return render_template('member_login.html', title='تسجيل الدخول ', form=form)

@app.route('/GP1routeRelease1', methods=['GET', 'POST'])
def adminlogin():
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
            session['role'] = user_role 
            if user_role == 'admin':
                flash('<i class="fas fa-check-circle me-3"></i> تم تسجيل دخولك كمسؤول', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('<i class="fas fa-times-circle me-3"></i> فشل تسجيل دخولك، راجع بريدك الإلكتروني وكلمة المرور', 'danger')

        except requests.exceptions.HTTPError as e:
            error_json = e.response.json()
            error_message = error_json.get('error', {}).get('message', 'مشكلة غير معروفة')
            flash(f'<i class="fas fa-times-circle me-3"></i> فشل تسجيل دخولك، راجع بريدك الإلكتروني وكلمة المرور', 'danger')
    return render_template('adsecretlogin.html', title='تسجيل الدخول', form=form)

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
        password = form.password.data
        company_name = form.company_name.data
        company_docs = request.files.get('company_docs')
        file_url = upload_file_to_firebase_storage(company_docs)

        registration_data = {
            'username': username,
            'email': email,
            'password': password,
            'company_name': company_name,
            'company_docs_url': file_url,
            'status' : 'under review'
        }

        db.reference('registration_requests').push(registration_data)

        flash('<i class="fas fa-check-circle me-3"></i> تم رفع طلبكم بنجاح، سيتم مراجعة طلبكم والتأكد من الوثائق المرفقة، الرجاء مراجعة بريدكم الوارد أو البريد غير الهام خلال الأيام القادمة لمعرفة حالة الطلب', 'success')
        return redirect(url_for('home'))
    else:
        return render_template('register_request.html', title='طلب تسجيل حساب', form=form)

def extract_and_preprocess_frames(video_path, max_frames=10, target_size=(299, 299)):
    cap = cv2.VideoCapture(video_path)
    frames = []
    processed_frames = []
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, frame_count // max_frames)
    blank_frame_count = 0
    max_blank_frames=4

    for i in range(0, frame_count, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        success, frame = cap.read()
        if success:
            frames.append(frame)
        if len(frames) == max_frames:
            break

    for frame in frames:
        detected_faces = detector(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        
        if detected_faces:
            face = detected_faces[0]
            x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()
            cropped_face = frame[y1:y2, x1:x2]
            resized_face = cv2.resize(cropped_face, target_size)
            processed_frames.append(resized_face)
            blank_frame_count = 0
        else:
            processed_frames.append(np.zeros((target_size[0], target_size[1], 3), dtype=np.uint8))
            blank_frame_count += 1 
            
            if blank_frame_count > max_blank_frames:
                print("No faces detected for too long. Stopping processing.")
                break

    cap.release()
    return np.array(processed_frames)

@app.route('/shayekModel',methods=['GET','POST'])
def shayekModel():
    if request.method == 'POST':
        if request.files:
            video = request.files['video']
            if video and video.filename != '':
                upload_folder = 'uploads'
                os.makedirs(upload_folder, exist_ok=True)
                video_path = os.path.join(upload_folder, video.filename)
                video.save(video_path)
                processed_frames = extract_and_preprocess_frames(video_path)
                if processed_frames.size == 0:
                    os.remove(video_path)
                    return jsonify({'error': 'لم نستطع إيجاد أوجه في الفيديو'})
                processed_frames = np.expand_dims(processed_frames, axis=0)
                pred = model.predict(processed_frames)[0][0]
                pred_label = 'الفيديو حقيقي' if pred <= 0.5 else 'الفيديو معدل'
                return jsonify({'result': pred_label})
            return jsonify({'error': 'لم يتم إرفاق ملف أو الملف المرفق تالف'})

    return render_template('shayekModel.html', title = 'نشيّك؟')

@app.route('/upload_video', methods=['GET','POST'])
def upload_video():
    if request.files:
        video = request.files['video']
        if video.filename != '':
            upload_folder = 'uploads'
            os.makedirs(upload_folder, exist_ok=True)
            video_path = os.path.join('uploads', video.filename)
            video.save(video_path)
            processed_frames = extract_and_preprocess_frames(video_path)
            if processed_frames.size == 0:
                return jsonify({'error': 'No faces detected or video is corrupted'})
            processed_frames = np.expand_dims(processed_frames, axis=0)
            pred = model.predict(processed_frames)[0][0]
            pred_label = 'الفيديو حقيقي' if pred <= 0.5 else 'الفيديو معدل'
            os.remove(video_path)
            return jsonify({'result': pred_label})
    return jsonify({'error': 'لم يتم إرفاق ملف أو الملف المرفق تالف'})

@login_manager.user_loader
def load_user(email):
    user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(email).get()
    
    if user_ref:
        user_data = next(iter(user_ref.values()), None)
        if user_data:
            user_data.pop('email', None)
            password_hash = user_data.pop('password', None)
            if password_hash:
                return User(email=email, password_hash=password_hash, **user_data)

    user_ref = db.reference('users').order_by_child('email').equal_to(email).get()
    
    if user_ref:
        user_data = next(iter(user_ref.values()), None)
        if user_data:
            user_data.pop('email', None)
            password_hash = user_data.pop('password', None)
            if password_hash:
                return User(email=email, password_hash=password_hash, **user_data) 
    flash('<i class="fas fa-times-circle me-3"></i> مشكلة في بيانات المستخدم، الرجاء المحاولة لاحقاً', 'danger')
    return None

class User(UserMixin):
    def __init__(self, email, password_hash, username=None, is_active=True, **kwargs):
        self.id = email
        self.email = email
        self.username = username or kwargs.get('username')
        self.password_hash = password_hash
        self.is_active = is_active

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    def get_id(self):
        return self.id 
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'shayekgp1@gmail.com'
app.config['MAIL_PASSWORD'] = 'ymujhammpqswenzl'
app.config['MAIL_DEFAULT_SENDER'] = 'shayekgp1@gmail.com'

mail = Mail(app)

@app.route('/verify_request/<request_id>', methods=['POST'])
def verify_request(request_id):
    if 'logged_in' in session and session['role'] == 'admin':
        ref_request = db.reference(f'registration_requests/{request_id}')
        request_data = ref_request.get()

        if request_data:
            email = request_data['email']
            subject = ""
            body = ""
            password_hash = generate_password_hash(request_data['password'])

            if 'decline' in request.form:
                ref_request.update({'status': 'declined', 'password': password_hash})
                subject = "رفض طلب تسجيل في منصة شيّــك"
                body = "عزيزنا/عزيزتنا {},\n\n" \
                       "نأسف لإشعاركم أنه لم يتم قبول طلب تسجيلكم في منصة شيّــك، " \
                       "الرجاء مراجعة الملف المرفق والتأكد من اكتمال المتطلبات وصحتها.".format(request_data['username'])

                flash('<i class="fas fa-check-circle me-3"></i> تم رفض الطلب بنجاح', 'info')
            elif 'accept' in request.form:
                new_user = auth.create_user(
                    email=request_data['email'],
                    password=request_data['password'],
                )
                user_data = {
                    'username': request_data['company_name'],
                    'email': request_data['email'],
                    'password': password_hash,
                    'is_newsoutlet': True
                }
                db.reference('newsoutlet').push(user_data)
                ref_request.update({'status': 'accepted', 'uid': new_user.uid, 'password': password_hash})                    
                subject = "تم قبول طلب تسجيلكم في منصة شيّــك"
                body = "عزيزنا/عزيزتنا {},\n\nتم قبول طلب تسجيلكم في منصة شيّــك".format(request_data['username'])
                flash('<i class="fas fa-check-circle me-3"></i> تم قبول طلب التسجيل وإنشاء الحساب', 'success')
            msg = Message(subject, recipients=[email], body=body)
            mail.send(msg)
            return f"<script>window.location.href = '{url_for('admin_dashboard')}';</script>"
        else:
            flash('<i class="fas fa-times-circle me-3"></i> لم نستطع إيجاد أي بيانات.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('login'))

@app.route('/submit_post', methods=['POST'])
@login_required
def submit_post():
    user_email = current_user.get_id()
    if not user_email:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('login'))

    user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(user_email).get()
    if not user_ref:
        flash('<i class="fas fa-times-circle me-3"></i> المستخدم غير موجود', 'danger')
        return redirect(url_for('login'))
    username = list(user_ref.values())[0].get('username')

    title = request.form['title']
    body = request.form['body']
    media = request.files.get('media')

    bucket = storage.bucket()

    media_url = None
    if media and media.filename:
        filename = secure_filename(media.filename)
        blob = bucket.blob(f'posts/{username}/{filename}')
        content_type = media.content_type
        if not content_type:
            extension = filename.split('.')[-1].lower()
            if extension == 'mp4':
                content_type = 'video/mp4'
            elif extension == 'webm':
                content_type = 'video/webm'
            elif extension == 'ogg':
                content_type = 'video/ogg'
            elif extension == 'mov':
                content_type = 'video/quicktime'
            else:
                content_type = 'application/octet-stream'

        blob.upload_from_file(media.stream, content_type=content_type)
        blob.make_public()
        media_url = blob.public_url

    timestamp = datetime.now()
    formatted_timestamp = timestamp.strftime("%b %d, %Y %I:%M%p")

    post_data = {
        'title': title,
        'body': body,
        'media_url': media_url,
        'author': username,
        'author_email': user_email,
        'timestamp': formatted_timestamp
    }

    db.reference('posts').push(post_data)

    flash('<i class="fas fa-check-circle me-3"></i> تم إضافة النشرة بنجاح', 'success')
    return redirect(url_for('user_home'))

@app.route('/delete_post/<string:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    user_email = current_user.get_id()
    if not user_email:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('login'))

    post_ref = db.reference(f'posts/{post_id}')
    post_ref.delete()

    flash('<i class="fas fa-check-circle me-3"></i> تم حذف النشرة بنجاح', 'success')
    return redirect(url_for('user_home'))

@app.route('/admin/logout')
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('role', None)
    session.pop('user_info', None) 
    flash('<i class="fas fa-check-circle me-3"></i> تم تسجيل خروجك بنجاح', 'success')
    return redirect(url_for('home'))

@app.route('/member_register', methods=['GET', 'POST'])
def member_register():
    form = UserRegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        try:
            user = auth.create_user(
                email=email,
                password=password
            )

            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            
            user_data = {
                'username': username,
                'email': email,
                'password' : hashed_password,
                'is_newsoutlet': False 
            }
            
            db.reference(f'users/{user.uid}').set(user_data)
            
            flash('<i class="fas fa-check-circle me-3"></i> تم تسجيل الحساب بنجاح', 'success')
            return redirect(url_for('member_login'))
        except Exception as e:
            flash(f'<i class="fas fa-times-circle me-3"></i> حدث خطأ: {str(e)}', 'danger')

    return render_template('member_register.html', form=form)

@app.route('/Member/home')
@login_required
def member_home():
    user_email = session.get('user_email')
    if user_email:
        user_data = load_user(user_email)
        if user_data:
            login_user(user_data) 
            posts = fetch_posts()  
            user_ref = db.reference('users').order_by_child('email').equal_to(user_email).get()
            if not user_ref:
                flash('<i class="fas fa-times-circle me-3"></i> المستخدم غير موجود', 'danger')
                return redirect(url_for('/Member/login'))
            username = list(user_ref.values())[0].get('username')
            return render_template('member_home.html', posts=posts, username=username)
        else:
            flash('<i class="fas fa-times-circle me-3"></i> يرجى تسجيل الدخول أولاً', 'danger')
            return redirect(url_for('login'))
    else:
        flash('<i class="fas fa-times-circle me-3"></i> يرجى تسجيل الدخول أولاً', 'danger')
        return redirect(url_for('login'))