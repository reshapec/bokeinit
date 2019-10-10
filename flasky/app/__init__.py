#!/usr/bin/python3

"""应用包的构造文件"""

from flask import Flask
from flask import render_template # 函数把Jinja2模板引擎集成到应用中
from flask_bootstrap import Bootstrap # 使用flask_bootstrap集成Bootstrap，创建整洁且具有吸引力的网站
from flask_mail import Mail # 使用flask_mail提供电子邮件支持
from flask_moment import Moment # 使用flask_moment本地化日期和时间
from flask_sqlalchemy import SQLAlchemy # 使用flask_sqlalchemy管理数据库
from config import config
from flask_login import LoginManager
from flask_pagedown import PageDown # 实现客户端Markdown到HTML转换程序
from flask_debugtoolbar import DebugToolbarExtension # 扩展Flask-DebugToolbar提供了一系列调试功能，可以用来查看请求的SQL语句、配置选项、资源加载情况等信息, 这些信息在开发时会非常有用

bootstrap = Bootstrap() # 此处初始化方式:应用实例作为参数传递给构造函数
mail = Mail() # 放在app.config后，不然配置不会生效,引起ConnectionRefusedError
moment = Moment() # 初始化flask-moment
db = SQLAlchemy() # SQLAlchemy类的实例，表示应用使用的数据库
login_manager = LoginManager() 
login_manager.login_view = 'auth.login' # LoginManager()对象的login_view属性用于设置登录页面的端点。匿名用户尝试访问受保护的页面时，Flask_Login将重定向到登录页面
pagedown = PageDown()
toolbar = DebugToolbarExtension()

def create_app(config_name): # 应用的工厂函数，参数:应用使用的配置名 
    app = Flask(__name__) 
    app.config.from_object(config[config_name]) # from_object()初始化应用
    config[config_name].init_app(app) 
    
    bootstrap.init_app(app) # 初始化扩展对象
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)
    toolbar.init_app(app)
   
    # 添加路由和自定义错误界面
    from .main import main as main_blueprint # 从当前main包中导入蓝本main,取别名
    app.register_blueprint(main_blueprint) # 注册主蓝本

    from .auth import auth as auth_blueprint # 从当前auth包中导入蓝本auth,取别名
    app.register_blueprint(auth_blueprint, url_prefix='/auth') # 注册身份验证蓝本

    return app

    
