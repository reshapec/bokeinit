#!/usr/bin/python3

"""电子邮件支持函数"""

from . import mail # 从当前包中导入Mail实例

"""异步发送电子邮件"""
from flask_mail import Message
from flask import render_template, current_app
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        # Flask-Mail的send()函数使用current_app,必须激活应用上下文
        # mail是一个Mail实例
        mail.send(msg) 

# send_email()的参数：收件人地址、主题、渲染邮件正文的模板、关键字参数列表
def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    # msg = Message(邮件标题、发送方、接收方)
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + '' + subject, sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    # 邮件内容会以文本和html两种格式呈现，而你能看到哪种格式取决于你的邮件客户端
    msg.boby = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


