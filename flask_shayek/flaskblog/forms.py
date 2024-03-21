from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo

class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=2, max=20)])
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة السر', validators=[DataRequired()])
    confirmPassword = PasswordField('تأكيد كلمة السر', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('تسجيل')

class LoginForm(FlaskForm):
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة السر', validators=[DataRequired()])
    remember = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')

class RegistrationRequestForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    company_name = StringField('اسم المنصة', validators=[DataRequired()])
    company_docs = FileField('وثائق المنصة', validators=[DataRequired()])
    verified = BooleanField('تم التحقق', default=False)  # Initially set to False
    submit = SubmitField('طلب فتح حساب')

    def toggle_verified_visibility(self):
        if hasattr(self, 'verified'):
            delattr(self, 'verified')
