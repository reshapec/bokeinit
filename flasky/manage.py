#!/usr/bin/python3

"""主脚本"""
from app import create_app, db
from app.models import Role, User, Post, Parent_child, Zan, Comment, Follow
from app.email import send_email
from flask_migrate import Migrate


app = create_app('default')
migrate = Migrate(app, db)

@app.shell_context_processor  
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Post=Post, Parent_child=Parent_child, Zan=Zan, Comment=Comment, Follow=Follow)


@app.cli.command()
def test(): 
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
