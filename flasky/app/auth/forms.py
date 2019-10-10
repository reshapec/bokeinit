#!/usr/bin/python3

"""身份验证蓝本中的登录表单"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User


class LoginForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('登录密码', validators=[DataRequired()])
    remember_me = BooleanField('keep me logged in')
    submit = SubmitField('提交')

class RegistrationForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, '用户名由字母、数字、下划线、点号组成')])
    password = PasswordField('登录密码', validators=[DataRequired()])
    password2 = PasswordField('确认登录密码', validators=[DataRequired(), EqualTo('password', message='两次设置的登录密码需要一致')])
    submit = SubmitField('注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('电子邮箱已经被注册')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已经被注册')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('原登录密码', validators=[DataRequired()])
    password = PasswordField('新登录密码', validators=[DataRequired()])
    password2 = PasswordField('确认新登录密码', validators=[DataRequired(), EqualTo('password', message='两次设置的登录密码需要一致')])
    submit = SubmitField('更新密码')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('请求重置密码')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('新登录密码', validators=[DataRequired()])
    password2 = PasswordField('确认新登录密码', validators=[DataRequired(), EqualTo('password', message='两次设置的登录密码需要一致')])
    submit = SubmitField('重置密码')


class ChangeEmailForm(FlaskForm):
    email = StringField('新邮箱', validators=[DataRequired(), Length(1, 64),
                                                 Email()])
    password = PasswordField('登录密码', validators=[DataRequired()])
    submit = SubmitField('更改电子邮件地址')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('电子邮箱已经被注册')
    
