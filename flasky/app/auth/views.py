#!/usr/bin/python3

from flask import render_template, redirect, request, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from . import auth 
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, ResetPasswordRequestForm, ResetPasswordForm, ChangeEmailForm
from ..models import User
from ..email import send_email
from .. import db


"""使用蓝本的route装饰器定义与身份验证相关的路由"""
"""
用户登录应用后，他们的验证状态要记录在用户会话中，这样浏览不同的页面时才能记住这个状态. flask_login是个非常有用的小型扩展，专门用于管理用户身份验证系统中的验证状态，且不依赖特定的身份机制
"""

# 登录路由
@auth.route('/login', methods=['GET', 'POST'])
def login():
    # 创建一个LoginForm()表单，用于表示表单
    form = LoginForm()
    # 如果提交的数据能被所有的验证函数接受，validate_on_submit()方法返回True, 进一步处理表单提交的数据
    if form.validate_on_submit():
        # 将表单email字段的data属性赋值给User模型的类属性email, 在数据库中查找是否存在该用户
        user = User.query.filter_by(email=form.email.data).first()
        # 如果用户存在，并通过了密码验证
        if user is not None and user.verify_password(form.password.data):
            # login_user()函数在用户会话中把用户标记为已登录，函数的参数是要登录的用户，和可选的"记住我"布尔值
            # login_user()函数把用户的id以字符串的形式写入用户会话
            # 关闭浏览器后用户会话过期，下次用户访问时要重新登录
            login_user(user, form.remember_me.data)
            # 发送名为login_in的信号, 发送信号调用send()方法，它接受一个发件者作为第一个参数和一些可选的被转发到信号用户的关键字参数
            login_in.send(auth, user=current_user._get_current_object())
            # 视图函数重定向到首页
            next = request.args.get('next') 
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        flash('用户名或登录密码无效')
    return render_template('auth/login.html', form=form)

# 创建信号(信号依赖于Blinker库，请确保已经安装; 使用唯一的信号名并且简化调试, 可以用name属性来访问信号名)
from blinker import Namespace 
my_signals = Namespace() 
login_in = my_signals.signal('login_in')

# 当信号通过auth连接时---即当sender为auth时，通过Blinker的connect_via()装饰器订阅名为login_in信号
# 发送信号被我设置在登录时完成---即一登录就会触发login_in信号的发送，将user=current_user._get_current_object()的关键字参数传递给订阅信号的函数，订阅函数内部完成设置的功能：增加登录次数，并添加最近登录的ip，给出相应的flash显示
@login_in.connect_via(auth)
def _track_logins(sender, user, **extra):
    user.login_count += 1
    user.last_login_ip = request.remote_addr
    db.session.add(user)
    db.session.commit()
    flash('{}欢迎进入本社区，登录次数: {}，IP: {}'.format(user.username, user.login_count, user.last_login_ip))


"""
在每次访问url_prefix='/auth'的路由时，都发送一条有关欢迎的信号
# 自定义信号
from blinker import Namespace
my_signals = Namespace()
login_in = my_signals.signal('login_in')

# 发送信号
@auth.before_request
def before_every_request_in_auth():
    login_in.send(auth, msg="欢迎光临本社区")

# 当信号通过auth连接时，也就是当sender为auth时，订阅信号
@login_in.connect_via(auth)
def _track_logins(sender, msg, **extra):
    flash(msg)
"""

# 退出路由
@auth.route('/logout')
@login_required
def logout():
    logout_user() # 从用户会话中把用户id删除
    flash('退出登录') # 闪现消息
    return redirect(url_for('main.index')) # 重定向到首页

# 发送确认邮件的注册路由
@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, 
                    username=form.username.data, 
                    password=form.password2.data)
        db.session.add(user)
        db.session.commit()
        # 生成包含用户id的签名令牌
        token = user.generate_confirmation_token() 
        # 给注册邮箱发送裹挟签名令牌的确认邮件
        send_email(user.email, '自习室注册验证', 'auth/email/confirm',  user=user, token=token)
        flash('已通过电子邮件向你发送确认邮件')
        # 重定向到首页
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)

# 确认用户账户的路由
@auth.route('/confirm/<token>')
@login_required # 保护'/confirm/<token>'路由，点击邮件链接的用户要先登录才能确认...
def confirm(token):
     if current_user.confirmed: # 检查已登录用户是否已经确认过
       return redirect(url_for('main.index'))
     if current_user.confirm(token): # 调用confirm()方法对已登录的用户进行账户确认，检验令牌
         db.session.commit()
         flash('安全验证已完成，谢谢！')
     else:
         flash('确认链接无效或已过期')
     return redirect(url_for('main.index'))

# 使用before_app_request处理程序, 来过滤未确认的账户
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        # 更新已登录用户的最后访问时间
        current_user.ping() 
        # 用户已登录且用户状态还未确认且请求的url不在身份验证蓝本中，也不是对静态文件的请求的情况下
        if not current_user.confirmed and request.blueprint != 'auth' and request.endpoint != 'static':
            # 重定向到/auth/unconfirmed路由
            return redirect(url_for('auth.unconfirmed'))

@auth.route('/unconfirmed') # auth/unconfirmed路由
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    # 显示html页面，页面包含一个链接，指向重新发送账户确认邮件的路由，用于请求发送新的确认邮件
    return render_template('auth/unconfirmed.html')

# 重新发送账户确认邮件的路由
@auth.route('confirm')
@login_required
def resend_confirmation():
    # 生成包含用户id的签名令牌
    token = current_user.generate_confirmation_token() 
    send_email(current_user.email, '自习室注册验证', 'auth/email/confirm',  user=current_user, token=token)
    flash('已向您发送一封新的确认邮件')
    return redirect(url_for('main.index'))

# 修改密码路由
@auth.route('change_password', methods=['GET', 'POST'])
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
    # 调用verify_password()方法，参数:表单里填写的原登录密码，与存储在数据库中的加密密文，确认结果为True后，可以同意用户更新密码的请求，生成新的加密密文，提交数据库会话
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password2.data
            db.session.add(current_user)
            db.session.commit()
            flash('您的密码已被更新')
            return redirect(url_for('main.index'))
        else:
            flash('无效密码')
    return render_template('auth/change_password.html', form=form)

# 请求重设密码的路由
@auth.route('/reset', methods=['GET', 'POST'])
def reset_password_request():
    if not current_user.is_anonymous: 
        return redirect(url_for('main.index'))
    # 渲染填写电子邮箱的表单
    form = ResetPasswordRequestForm() 
    if form.validate_on_submit():
        # 使用表单中填写的电子邮件地址从数据库加载用户
        user = User.query.filter_by(email=form.email.data.lower()).first()
        # 如果用户存在
        if user:
            # 生成包含用户id的重置的签名令牌
            token = user.generate_reset_token() 
            send_email(user.email, '自习室重设密码验证', 'auth/email/reset_password', user=user,
token=token)
        flash('一封包含重置密码指令的电子邮件已经发送给您')
        # 重定向到用户登录页面
        return redirect(url_for('auth.login')) 
    return render_template('auth/reset_password_request.html', form=form)

# 重置密码的路由
@auth.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if not current_user.is_anonymous: 
        return redirect(url_for('main.index'))
    # 渲染重置密码的表单
    form = ResetPasswordForm() 
    if form.validate_on_submit():
        # 确认重设令牌的工作在User模型中完成
        if User.reset_password(token, form.password2.data):
            db.session.commit()
            flash('您的密码已重置')
            # 重定向到用户登录页面
            return redirect(url_for('auth.login'))
        else:
            # 重定向到首页
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)
  
# 修改电子邮件地址的路由，用户已登录的情况下      
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
