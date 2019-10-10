#!/usr/bin/python3

"""检查用户权限的自定义装饰器"""
"""让视图函数只对具有特定权限的用户开放"""

from functools import wraps
from flask import abort
from flask_login import current_user
from .models import Permission

# 检查常规权限
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 如果用户不具有指定权限，返回403响应
            if not current_user.can(permission):
                abort(403) 
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 检查管理员权限
def admin_required(f):
    return permission_required(Permission.ADMIN)(f)
