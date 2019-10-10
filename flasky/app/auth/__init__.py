#!/usr/bin/python3

"""创建身份验证蓝本"""

from flask import Blueprint

auth = Blueprint('auth', __name__) # 蓝本auth通过实例化一个Blueprint类创建

from . import views # 从当前包中导入views模块，将路由与蓝本关联起来
