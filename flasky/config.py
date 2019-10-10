#!/usr/bin/python3

"""应用的配置"""

from info import username, password
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'xxx' 
    MAIL_DEBUG = True
    MAIL_SERVER = 'smtp.qq.com' 
    MAIL_PORT = 465 
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = username
    MAIL_PASSWORD = password
    FLASKY_MAIL_SUBJECT_PREFIX = 'xxx' 
    FLASKY_MAIL_SENDER = 'xxx'
    FLASKY_ADMIN = username
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False 
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI =\
    'sqlite://'

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    
    'default': DevelopmentConfig
    }
