#!/usr/bin/python3

"""数据库模型"""

from . import db, login_manager 
from werkzeug.security import generate_password_hash, check_password_hash # 从Werkzeug中的security模块导入generate_password_hash()函数和check_password_hash()函数，分别用在注册和核对两个阶段
from flask_login import UserMixin # 从Flask-Login扩展中导入UserMixin类，满足多数Flask-Login要求应用的User模型必须实现的几个属性和方法：is_authenticated、is_active、is_anonymous、get_id()
from flask_login import AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer # 确认用户账户
from flask import current_app, request
from datetime import datetime
import hashlib
from markdown import markdown
import bleach

"""@login_manage.user_loader装饰器把load_user()函数注册给Flask-Login, 在Flask-Login扩展需要获取登录用户的信息时调用"""
# 加载用户的函数
from . import login_manager
@login_manager.user_loader 
def load_user(user_id):
    return User.query.get(int(user_id)) # 将用户标识符转为整数，传递给Flask-SQLAlchemy查询，加载用户；SQLAlchemy查询执行方法get()返回指定主键对应的行

# 权限常量
class Permission:
    # 设置类属性
    FOLLOW = 1      # 关注用户
    COMMENT = 2     # 发表评论
    ZAN = 4         # 点赞
    WRITE = 8       # 写文章
    MODERATE = 16   # 管理他人发表的评论
    ADMIN = 32      # 管理员权限

# 定义角色模型
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        # 让子类Role的实例包含父类db.Model的所有属性
        super(Role, self).__init__(**kwargs) 
        if self.permissions is None:
            self.permissions = 0 

    def add_permission(self, perm): # 添加权限
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm): # 移除权限
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self): # 重置权限
        self.permissions = 0

    def has_permission(self, perm): # 检查组合权限中是否包含单独的权限
        return self.permissions & perm == perm

    """在数据库中创建角色"""
    @staticmethod
    # insert_roles()是静态方法，在类上直接调用，如Role.insert_roles()
    # 与实例方法不同的是，静态方法中的参数中没有self
    def insert_roles(): 
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.ZAN, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.ZAN, Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.ZAN, Permission.WRITE,
Permission.MODERATE, Permission.ADMIN],
        }
        default_role = 'User'
        # 遍历roles字典中的键, i依次为'User'、'Moderator'、'Administrator'
        for i in roles:
            # 发起查询，加载名为"i"的用户角色，没有结果则返回None
            try:
                role = Role.query.filter_by(name=i).first()
            except InvalidRequestError:
                db.session.rollback()
            else:
                if role is None: # 如果数据库中没有该角色名
                    role = Role(name=i) # 创建新角色对象, Role模型的实例
                role.reset_permissions() 
                for perm in roles[i]: # 遍历roles字典指定键i对应的值列表
                    role.add_permission(perm) # 赋予新角色对象对应的一系列权限
                role.default = (role.name == default_role)
                db.session.add(role) # 将新角色对象添加至会话中
        db.session.commit() # 提交会话

    def __repr__(self):
        return '<Role %r>' % self.name

# 关注关系中关联表的模型实现
class Follow(db.Model):
    __tablename__ = 'follows'
    # 主动关注的人的id
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    # 被关注者的id
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# 用户模型
class User(db.Model, UserMixin):
    __tablename__='users'
    # 直接在class中定义属性，这种属性是类属性，归User类所有，但类的所有实例都可访问
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128)) # 保存加密后的密文
    confirmed = db.Column(db.Boolean, default=False) # 保存确认用户账户的信息
    # 新添一些字段，在数据库中存储用户的一些额外信息
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    # 新添类属性avatar_hash,用于缓存图片的路径
    avatar_hash = db.Column(db.String(64))
    avatar_hash_2 = db.Column(db.String(64))
    # 新添字段，登录次数和最近登录ip
    login_count = db.Column(db.Integer, default=0)
    last_login_ip = db.Column(db.String(128), default='unknown')
    # 新添posts字段，反映一对多关系，一个用户可以有多篇文章
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    # 新添字段，使用两个一对多关系实现的多对多关系，不是真正的User模型类属性，但可以直接使用
    # followed表示已经关注的人
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    # followers表示自己的粉丝
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    # 新添comments字段，构建users表和comments表之间的一对多关系
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    # 新添zans字段，构建users表和zans表之间的一对多关系
    zans = db.relationship('Zan', backref='author', lazy='dynamic')
    
    

    """@property装饰器负责把一个方法变成属性调用"""
    @property
    # 获取所关注用户的文章
    def idols_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)

    # 把用户设为自己的关注者
    @staticmethod
    def add_self_idols():
        for user in User.query.all():
            user.follow(user)
            db.session.add(user)
            db.session.commit()
   
    # 刷新用户的最后访问时间，将ping()函数放在auth蓝本中的before_app_request中
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    """定义默认的用户角色: 用户在应用中注册账户时，应该赋予其适当的角色"""
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # role属性也可使用，虽然不是真正的数据库列，但却是一对多关系的高级表示
        if self.role is None: 
            if self.email == current_app.config['FLASKY_ADMIN']:
                # 发起查询，加载名为"Administrator"的用户角色,赋值给实例的role属性
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            # 将默认图片的路径存放在avatar_hash中，用户一旦注册，赋初始值
            self.avatar_hash = 'images/default_avatar.jpg'
            self.avatar_hash_2 = 'images/2default_avatar.jpg'

    # 检验用户是否具有指定的权限
    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)
    
    # 检验用户是否具有管理员权限
    def is_administrator(self):
        return self.can(Permission.ADMIN)
                    
    def __repr__(self):
        return '<User %r>' %self.username
    
    """@property装饰器负责把一个方法变成属性调用"""
    # 把一个getter方法变成属性，只需要加上@property就可以
    # 当前password()方法通过@property装饰器已经变成password属性，可读
    # 设置一旦读取password属性的值，抛出AttributeError异常，即外部无法访问
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    # @property装饰器本身又创建了另一个装饰器@password.setter，把一个setter方法变成属性赋值，可写入明文密码 
    # 赋值方法调用相关函数将明文密码password转成密文(密码散列值)存储到USer模型的password_hash字段
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    # 定义验证密码的verity_password()方法，方法内部调用check_password_hash()函数
    # 将输入的密码与存储在USer模型中的密码散列值进行对比，方法返回True,表明密码是正确的
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 使用itsdangerous生成包含用户id的签名令牌
    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({ 'confirm': self.id }).decode('utf-8')

    # 检验令牌
    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    # 使用itsdangerous生成包含用户id的重置的签名令牌
    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    # 检验重置令牌
    @staticmethod # 此注释可表明使用类名可以直接调用该方法
    def reset_password(token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    # 修改电子邮件地址的生成和检验令牌的功能
    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps(
            {'change_email': self.id, 'new_email': new_email}).decode('utf-8')

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = 'images/default_avatar.jpg'
        self.avatar_hash_2 = 'images/2default_avatar.jpg'
        db.session.add(self)
        return True
        
    """关注关系的辅助方法"""
    # 关注功能
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    # 取消关注功能
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    # 状态：是否已经关注
    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    # 状态： 是否已经被关注
    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

# 匿名用户类
class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False
# 将Flask-Login的anonymous_user属性设置成应用自定义的匿名用户类
login_manager.anonymous_user = AnonymousUser 

# 博客文章模型
class Post(db.Model):
    __tablename_ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    # 新增body_html字段，缓存转换后的博客文章HTML代码
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    # 增加字段top，做为标识是否为置顶的文章，用于分类（置顶为1,没有置顶为0）
    top = db.Column(db.Boolean, default=False, index=True)
    # 新添comments字段，构建posts表和comments表之间的一对多关系
    comments = db.relationship('Comment', backref='post', lazy='dynamic') 
    # 新添zans字段，构建posts表和zans表之间的一对多关系
    zans = db.relationship('Zan', backref='post', lazy='dynamic')
    # 处理Markdown文本
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))  
    
    # 把一个getter()方法变成属性调用，联结过滤查询针对博客的评论
    @property
    def comments_of_post(self):
        return Comment.query.join(Parent_child, Parent_child.child_id == Comment.id).filter(Parent_child.parent_id == self.id)

db.event.listen(Post.body, 'set', Post.on_changed_body)

# 父子表关系模型
class Parent_child(db.Model):
    # parent_children表记录评论表中各个评论的父子关系
    __tablename__ = 'parent_child'
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('comments.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
 
# 评论模型
class Comment(db.Model):
    # comments表保存所有评论内容
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    # 一对多关系的实现: 在"多"这一侧加入一个外键， 指向"一"这一侧连接的记录
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    # 新添字段，使用两个一对多关系实现的多对多关系
    parent = db.relationship('Parent_child',
                             foreign_keys=[Parent_child.child_id],
                             backref=db.backref('child', lazy='joined'),
                             lazy='dynamic',
                             cascade='all, delete-orphan')
    child = db.relationship('Parent_child',
                             foreign_keys=[Parent_child.parent_id],
                             backref=db.backref('parent', lazy='joined'),
                             lazy='dynamic',
                             cascade='all, delete-orphan')
    # 仿贴吧楼层，对指定博客的所有评论内容顺序排序, 功能已完善
    float_id = db.Column(db.Integer, default='0')
    # 新添zans字段，构建comments表和zans表之间的一对多关系
    zans = db.relationship('Zan', backref='comment', lazy='dynamic')
    # 类实例方法
    # 被回复者用户名，遍历父子关系表：针对博客的评论，返回博客作者名; 针对评论的评论，返回发表父评论的作者名
    def relayedname(self, parent_childs):
        for parent_child in parent_childs:
            if parent_child.parent_id == self.post_id and parent_child.child_id == self.id:
                return self.post.author.username
            if parent_child.parent_id != self.post_id and parent_child.child_id == self.id:
                # 如果博客的评论表中存在评论id等于父评论id,即该评论是对应的父评论，返回发表父评论的作者名
                for item in self.post.comments:
                    if parent_child.parent_id == item.id:
                        return item.author.username
          
    # 静态方法，在类上直接调用  
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))
    
    
db.event.listen(Comment.body, 'set', Comment.on_changed_body)

# 点赞模型
class Zan(db.Model):
    # zans表保存所有点赞内容
    __tablename__ = 'zans'
    # 主键
    id = db.Column(db.Integer, primary_key=True)
    # 点赞时间
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # 用户id
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # 点赞状态：0-取消，1-有效
    status = db.Column(db.Boolean)
    # 点赞类型：'post'博文点赞; 'comment'评论点赞
    type = db.Column(db.String(64), index=True)
    # 点赞id, 根据点赞类型确认点赞id
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))

