#!/usr/bin/python3

"""主脚本"""
from app import create_app, db
from app.models import Role, User, Post, Parent_child, Zan, Comment, Follow
from app.email import send_email
from flask_migrate import Migrate


app = create_app('default') # 使用开发配置创建应用
migrate = Migrate(app, db)

# 创建并注册一个shell上下文处理器，让flask shell自动导入数据库实例和模型
@app.shell_context_processor  
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Post=Post, Parent_child=Parent_child, Zan=Zan, Comment=Comment, Follow=Follow)

# 启动单元测试的命令
@app.cli.command() # 自定义命令，被装饰的函数名即命令名
def test(): 
    """Run the unit tests."""
    # test()函数的定义体中调用了unittest包提供的测试运行程序
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
