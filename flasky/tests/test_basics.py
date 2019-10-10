#!/usr/bin/python3

"""单元测试"""
import unittest
from flask import current_app 
from app import create_app, db 

class BasicsTestCase(unittest.TestCase):
    def setup(self):
        self.app = create_app('testing') # 使用测试配置创建应用
        self.app_context = self.app.app_context() # 获取应用上下文
        self.app_context.push() # 激活应用上下文
        db.create_all() # 在测试数据库中创建对应的表
        
    def teardown(self):
        db.session.remove()
        db.drop_all() # 删除测试数据库
        self.app_context.pop() # 删除应用上下文

    def test_app_exists(self): # 确保应用实例存在
        self.assertFalse(current_app is None)

    def test_app_is_testing(self): # 确保应用在测试配置中运行
        self.assertTrue(current_app.config['TESTING']) #此测试会失败，主脚本中的应用为开发配置:app = create_app('default'); 1. 此测试中'TESTING'改'DEBUG'则成功; 2. 主脚本中改app = create_app('testing')则成功.

