#!/usr/bin/python3

"""创建主蓝本"""

from flask import Blueprint

main = Blueprint('main', __name__) # 蓝本main通过实例化一个Blueprint类创建

from . import views, errors # 从当前包中导入views、errors模块，将路由和错误处理程序与蓝本关联起来


from ..models import Permission # 从上级包中导入Permission类

# 把Permission类加入模板上下文
# 在模板中可能也需要检查权限，所以Permission类的所有常量要能在模板中访问
@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)
