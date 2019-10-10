#!/usr/bin/python3

"""应用的配置"""

from info import username, password
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 配置Flask-WTF,给应用配置密钥
    SECRET_KEY = 'hard to guess string' 
    # 配置应用，使用QQ账户发送电子邮件(使用QQ邮箱SMTP服务器)
    MAIL_DEBUG = True # 开启debug，便于调试看信息
    MAIL_SERVER = 'smtp.qq.com' #  邮箱服务器
    MAIL_PORT = 465 # 端口
    MAIL_USE_SSL = True # 重要，qq邮箱需要使用SSL
    MAIL_USE_TLS = False # 不需要使用TLS
    MAIL_USERNAME = username # 填邮箱
    MAIL_PASSWORD = password # 填客户端授权码
    FLASKY_MAIL_SUBJECT_PREFIX = '[Python自习室]' # 定义邮件主题前缀
    FLASKY_MAIL_SENDER = 'Python自习室 Admin <1140383581@qq.com>' # 定义发件人地址
    FLASKY_ADMIN = username # 定义管理员地址
    SQLALCHEMY_TRACK_MODIFICATIONS = False #不需要跟踪对象变化时降低数据库内存消耗
    DEBUG_TB_INTERCEPT_REDIRECTS = False 
    
    @staticmethod # 此注释可表明使用类名可以直接调用该方法
    def init_app(app): # 执行当前需要的环境的初始化
        pass

class DevelopmentConfig(Config): # 开发环境
    DEBUG = True
    SQLALCHEMY_DATABASE_URI =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')

class TestingConfig(Config): # 测试环境
    TESTING = True
    SQLALCHEMY_DATABASE_URI =\
    'sqlite://'

class ProductionConfig(Config): # 生产环境
    SQLALCHEMY_DATABASE_URI =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    
    'default': DevelopmentConfig
    }
