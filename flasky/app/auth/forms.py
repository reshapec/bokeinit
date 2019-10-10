#!/usr/bin/python3

"""身份验证蓝本中的登录表单"""
from flask_wtf import FlaskForm # 导入FlaskForm基类

from wtforms import StringField, PasswordField, BooleanField, SubmitField
# 从wtforms包导入:文本字段、密码文本字段、复选框(值为True和False)、表单提交按钮

from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo # 从wtforms包导入验证函数: 确保转换类型后字段中有数据、验证输入字符串的长度、验证电子邮件地址、使用正则表达式验证输入值、比较两个字段的值;常用于要求输入两次密码进行确认的情况

from wtforms import ValidationError
from ..models import User

# 登录表单
class LoginForm(FlaskForm):
    # StringField类表示属性为type="text"的HTML <input> 元素
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    # PasswordField类表示属性为type="Password"的HTML <input> 元素
    password = PasswordField('登录密码', validators=[DataRequired()])
    # PasswordField类表示复选框
    remember_me = BooleanField('keep me logged in')
    # SubmitField类表示属性为type="submit"的HTML <input> 元素
    submit = SubmitField('提交')

# 注册表单
class RegistrationForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, '用户名由字母、数字、下划线、点号组成')])
    password = PasswordField('登录密码', validators=[DataRequired()])
    password2 = PasswordField('确认登录密码', validators=[DataRequired(), EqualTo('password', message='两次设置的登录密码需要一致')])
    submit = SubmitField('注册')

    # 为email字段定义的自定义验证函数，和常规的验证函数一起调用，确保填写的值在数据库中没出现过
    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('电子邮箱已经被注册')

    # 为username字段定义的自定义验证函数，和常规的验证函数一起调用，确保填写的值在数据库中没出现过
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已经被注册')

# 修改密码表单
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('原登录密码', validators=[DataRequired()])
    password = PasswordField('新登录密码', validators=[DataRequired()])
    password2 = PasswordField('确认新登录密码', validators=[DataRequired(), EqualTo('password', message='两次设置的登录密码需要一致')])
    submit = SubmitField('更新密码')

# 忘记密码后，请求重置密码的表单
class ResetPasswordRequestForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('请求重置密码')

# 重置密码的表单
class ResetPasswordForm(FlaskForm):
    password = PasswordField('新登录密码', validators=[DataRequired()])
    password2 = PasswordField('确认新登录密码', validators=[DataRequired(), EqualTo('password', message='两次设置的登录密码需要一致')])
    submit = SubmitField('重置密码')

# 修改电子邮箱的表单
class ChangeEmailForm(FlaskForm):
    email = StringField('新邮箱', validators=[DataRequired(), Length(1, 64),
                                                 Email()])
    password = PasswordField('登录密码', validators=[DataRequired()])
    submit = SubmitField('更改电子邮件地址')

    # 为email字段定义的自定义验证函数，和常规的验证函数一起调用，确保填写的值在数据库中没出现过
    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('电子邮箱已经被注册')
    
