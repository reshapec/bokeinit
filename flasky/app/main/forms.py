#!/usr/bin/python3

"""主蓝本中的表单"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms import BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, Regexp
from ..models import User, Role
from  flask_pagedown.fields import PageDownField

# 博客文章表单
class PostForm(FlaskForm):
    body = PageDownField("自由记录", validators=[DataRequired()])
    submit = SubmitField('提交')

# 评论输入表单
class CommentForm(FlaskForm):
    body = PageDownField("", validators=[DataRequired()])
    submit = SubmitField('提交')

# 回复输入表单
class ReplyForm(FlaskForm):
    body = StringField("", validators=[DataRequired()])
    submit = SubmitField('提交')

# 普通用户使用的资料编辑表单
class EditProfileForm(FlaskForm):
    name = StringField('真实姓名', validators=[Length(0, 64)])
    location = StringField('地区', validators=[Length(0, 64)])
    about_me = TextAreaField('简介')
    submit=SubmitField('提交')

# 管理员使用的资料编辑表单
class EditProfileAdminForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, '用户名由字母、数字、下划线、点号组成')])
    confirmed = BooleanField('确认状态')
    role = SelectField('角色', coerce=int)
    name = StringField('真实姓名', validators=[Length(0, 64)])
    location = StringField('地区', validators=[Length(0, 64)])
    about_me = TextAreaField('简介')
    submit=SubmitField('提交')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()] # SelectField实例必须在其choices属性中设置各选项
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email:
            if User.query.filter_by(email=field.data).first():
                return ValidationError('电子邮箱已经被注册')

    def validate_username(self, field):
        if field.data != self.user.username:
            if User.query.filter_by(username=field.data).first():
                return ValidationError('用户名已经被注册')


    
