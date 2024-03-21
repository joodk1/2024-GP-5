import os
from uuid import uuid4
from flask import current_app as app
from flask import render_template, url_for, flash, redirect, request, Flask
from flaskblog import app, firebase
from flaskblog.forms import RegistrationForm, LoginForm, RegistrationRequestForm
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, db, firestore, storage

# Firebase Admin SDK Initialization
cred = credentials.Certificate(r'C:\Users\huaweii\OneDrive\Documents\GitHub\2024-GP-5\flask_shayek\shayek-560ec-firebase-adminsdk-b0vzc-d1533cb95f.json')
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
    return render_template('about.html', title = '؟من نحن')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash(f'تم تسجيل حساب باسم {form.username.data}!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', title='استمارة التسجيل', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.email.data == 'admin@shayek.com' and form.password.data == 'password':
            flash('تم تسجيل دخولك بنجاح', 'success')
            return redirect(url_for('home'))
        else:
            flash('فشل تسجيل دخولك، راجع بريدك الإلكتروني وكلمة المرور', 'danger')
    return render_template('login.html', title='تسجيل الدخول', form=form)

def upload_file_to_firebase_storage(file):
    if file:
        # Ensure the filename is secure
        filename = secure_filename(file.filename)
        # Create a reference to the upload path
        bucket = storage.bucket()
        blob = bucket.blob(f"company_docs/{filename}")
        # Upload the file
        blob.upload_from_string(file.read(), content_type=file.content_type)
        # Make the blob publicly viewable
        blob.make_public()
        # Return the gs:// URL
        return f"gs://shayek-560ec.appspot.com/company_docs/{filename}"

@app.route('/register_request', methods=['GET', 'POST'])
def register_request():
    form = RegistrationRequestForm()
    if form.validate_on_submit():
        # Process form data
        username = form.username.data
        email = form.email.data
        company_name = form.company_name.data
        company_docs = request.files.get('company_docs')
        file_url = upload_file_to_firebase_storage(company_docs)

        # Prepare the data for Firebase, including the file path
        registration_data = {
            'username': username,
            'email': email,
            'company_name': company_name,
            'company_docs_url': file_url,
            'verified': False,  # Initial verification status
        }

        # Save the registration data to Firebase Realtime Database
        db.reference('registration_requests').push(registration_data)

        flash('Your request has been submitted successfully!', 'success')
        return redirect(url_for('home'))
    else:
        return render_template('register_request.html', title='Register Request', form=form)


@app.route('/shayekModel')
def shayekModel():
    return render_template('shayekModel.html', title = 'نشيّك؟')