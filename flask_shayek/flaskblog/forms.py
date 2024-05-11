from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp

class LoginForm(FlaskForm):
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    submit = SubmitField('تسجيل الدخول')

class RegistrationRequestForm(FlaskForm):
    username = StringField('الاسم الثنائي', validators=[DataRequired()])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[
        DataRequired(),
        Length(min=8, max=20, message='يجب أن تكون كلمة المرور بين 8 و20 حرفًا'),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+{}|:"<>?`\-=[\]\\\';,./])(?=.*\d).+$',
               message='يجب أن تحتوي كلمة المرور على حرف صغير وحرف كبير ورمز خاص ورقم واحد على الأقل')
    ])
    confirmPassword = PasswordField('تأكيد كلمة المرور', validators=[
        DataRequired(),
        EqualTo('password', message='يجب أن تتطابق كلمة المرور')
    ])
    company_name = StringField('اسم المنصة', validators=[DataRequired()])
    company_docs = FileField('وثائق المنصة', validators=[DataRequired()])
    verified = BooleanField('تم التحقق', default=False)
    submit = SubmitField('طلب فتح حساب')

    def toggle_verified_visibility(self):
        if hasattr(self, 'verified'):
            delattr(self, 'verified')