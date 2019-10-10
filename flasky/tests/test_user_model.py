#!/usr/bin/python3

"""密码散列测试"""

import unittest
from app.models import User, Role, Permission, AnonymousUser
from app import create_app, db

class UserModelTsetCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing') # 使用测试配置创建应用
        self.app_context = self.app.app_context() # 获取应用上下文
        self.app_context.push() # 激活应用上下文
        db.create_all() # 在测试数据库中创建对应的表
        Role.insert_roles() # 创建3类角色对象，在Role类上调用静态方法insert_roles()

    def tearDown(self):
        db.session.remove()
        db.drop_all() # 删除测试数据库
        self.app_context.pop() # 删除应用上下文

    def test_password_setter(self): # 测试赋值方法是否存入加密密文
        u = User(password='cat')
        self.assertTrue(u.password_hash is not None)

    def test_no_password_getter(self): # 测试password属性是否可读
        u = User(password='cat')
        with self.assertRaises(AttributeError):
            u.password

    def test_password_verification(self): # 测试验证函数是否有效
        u = User(password='cat')
        self.assertTrue(u.verify_password('cat'))
        self.assertFalse(u.verify_password('dog'))

    def test_password_salts_are_random(self): # 明文密码同，盐值不同，加密密文不同
        u1 = User(password='cat')
        u2 = User(password='cat')
        self.assertTrue(u1.password_hash != u2.password_hash)

    def test_user_role(self): # 测试用户权限
        u = User(email='1061414792@qq.com', password='cat')
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertTrue(u.can(Permission.COMMENT))
        self.assertTrue(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_moderator_role(self): # 测试协管员的权限
        r = Role.query.filter_by(name='Moderator').first()
        u = User(email='1061414792@qq.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertTrue(u.can(Permission.COMMENT))
        self.assertTrue(u.can(Permission.WRITE))
        self.assertTrue(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_administrator_role(self): # 测试管理员的权限
        r = Role.query.filter_by(name='Administrator').first()
        u = User(email='1061414792@qq.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertTrue(u.can(Permission.COMMENT))
        self.assertTrue(u.can(Permission.WRITE))
        self.assertTrue(u.can(Permission.MODERATE))
        self.assertTrue(u.can(Permission.ADMIN))

    def test_anonymous_user(self): # 测试匿名权限
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.FOLLOW))
        self.assertFalse(u.can(Permission.COMMENT))
        self.assertFalse(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))


