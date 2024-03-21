from flask import render_template, url_for, flash, redirect
from flaskblog import app
from flaskblog.forms import RegistrationForm, LoginForm, RegistrationRequestForm

posts = [
    {
        'author': 'صحييفة مكة',
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