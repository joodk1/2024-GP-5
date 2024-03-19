from flask import render_template, url_for, flash, redirect
from flaskblog import app
from flaskblog.forms import RegistrationForm, LoginForm, RegistrationRequestForm
from flaskblog.models import User, Post

posts = [
    {
        'author': 'شيّـــك',
        'title': 'النشرة الأولى',
        'content': 'تجربة',
        'date_posted': 'Mar 16, 2024'

    },
    {
        'author': 'جريدة الرياض',
        'title': 'أخبار اليوم',
        'content': 'مرحبًا شيّـــك',
        'date_posted': 'Mar 17, 2024'

    }
]

@app.route('/')
@app.route('/homepage')
def home():
    return render_template('home.html', posts=posts)


@app.route('/about')
def about():
    return render_template('about.html', title = 'من نحن')

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


@app.route('/register_request', methods=['GET', 'POST'])
def register_request():
    form = RegistrationRequestForm()
    if form.validate_on_submit():
        flash(f' تم ارسال الطلب {form.username.data}!', 'success')
        return redirect(url_for('home'))
    return render_template('register_request.html', title= 'فتح حساب منصة اخبارية', form=form)