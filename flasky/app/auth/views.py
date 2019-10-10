#!/usr/bin/python3

from flask import render_template, redirect, request, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from . import auth 
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, ResetPasswordRequestForm, ResetPasswordForm, ChangeEmailForm
from ..models import User
from ..email import send_email
from .. import db

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data)
            login_user(user, form.remember_me.data)
            next = request.args.get('next') 
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        flash('用户名或登录密码无效')
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user() 
    flash('退出登录')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, 
                    username=form.username.data, 
                    password=form.password2.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token() 
        send_email(user.email, '自习室注册验证', 'auth/email/confirm',  user=user, token=token)
        flash('已通过电子邮件向你发送确认邮件')
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
     if current_user.confirmed: 
       return redirect(url_for('main.index'))
     if current_user.confirm(token):
         db.session.commit()
         flash('安全验证已完成，谢谢！')
     else:
         flash('确认链接无效或已过期')
     return redirect(url_for('main.index'))

@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping() 
        if not current_user.confirmed and request.blueprint != 'auth' and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

@auth.route('confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token() 
    send_email(current_user.email, '自习室注册验证', 'auth/email/confirm',  user=current_user, token=token)
    flash('已向您发送一封新的确认邮件')
    return redirect(url_for('main.index'))

@auth.route('change_password', methods=['GET', 'POST'])
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password2.data
            db.session.add(current_user)
            db.session.commit()
            flash('您的密码已被更新')
            return redirect(url_for('main.index'))
        else:
            flash('无效密码')
    return render_template('auth/change_password.html', form=form)

@auth.route('/reset', methods=['GET', 'POST'])
def reset_password_request():
    if not current_user.is_anonymous: 
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm() 
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.generate_reset_token() 
            send_email(user.email, '自习室重设密码验证', 'auth/email/reset_password', user=user,
token=token)
        flash('一封包含重置密码指令的电子邮件已经发送给您')
        return redirect(url_for('auth.login')) 
    return render_template('auth/reset_password_request.html', form=form)

@auth.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if not current_user.is_anonymous: 
        return redirect(url_for('main.index'))
    form = ResetPasswordForm() 
    if form.validate_on_submit():
        if User.reset_password(token, form.password2.data):
            db.session.commit()
            flash('您的密码已重置')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)
    
@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data.lower()
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, '自习室修改电邮地址验证', 'auth/email/change_email',
                       user=current_user, token=token)
            flash('我们已向您发送一封电子邮件，其中包含确认新电子邮件地址的说明')
            return redirect(url_for('main.index'))
        else:
            flash('无效的电子邮件或密码')
    return render_template("auth/change_email.html", form=form)

@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        db.session.commit()
        flash('您的电子邮件地址已更新')
    else:
        flash('非法请求')
    return redirect(url_for('main.index'))
