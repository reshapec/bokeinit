#!/usr/bin/python3



from . import db, login_manager 
from werkzeug.security import generate_password_hash, check_password_hash 
from flask_login import UserMixin 
from flask_login import AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer 
from flask import current_app, request
from datetime import datetime
import hashlib
from markdown import markdown
import bleach


from . import login_manager
@login_manager.user_loader 
def load_user(user_id):
    return User.query.get(int(user_id))


class Permission:
    FOLLOW = 1    
    COMMENT = 2   
    ZAN = 4     
    WRITE = 8     
    MODERATE = 16 
    ADMIN = 32 


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs) 
        if self.permissions is None:
            self.permissions = 0 

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm
    
    @staticmethod
        def insert_roles(): 
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.ZAN, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.ZAN, Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.ZAN, Permission.WRITE,
Permission.MODERATE, Permission.ADMIN],
        }
        default_role = 'User'
        for i in roles:
            try:
                role = Role.query.filter_by(name=i).first()
            except InvalidRequestError:
                db.session.rollback()
            else:
                if role is None:
                    role = Role(name=i) 
                role.reset_permissions() 
                for perm in roles[i]:
                    role.add_permission(perm)
                role.default = (role.name == default_role)
                db.session.add(role) 
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model, UserMixin):
    __tablename__='users' 
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(64))
    avatar_hash_2 = db.Column(db.String(64))
    login_count = db.Column(db.Integer, default=0)
    last_login_ip = db.Column(db.String(128), default='unknown')
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    zans = db.relationship('Zan', backref='author', lazy='dynamic')
    
    @property
    def idols_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)

    @staticmethod
    def add_self_idols():
        for user in User.query.all():
            user.follow(user)
            db.session.add(user)
            db.session.commit()
   
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None: 
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = 'images/default_avatar.jpg'
            self.avatar_hash_2 = 'images/2default_avatar.jpg'

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)
 
    def is_administrator(self):
        return self.can(Permission.ADMIN)
                    
    def __repr__(self):
        return '<User %r>' %self.username
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({ 'confirm': self.id }).decode('utf-8')

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

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    @staticmethod 
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
   
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser 


class Post(db.Model):
    __tablename_ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    top = db.Column(db.Boolean, default=False, index=True)
    comments = db.relationship('Comment', backref='post', lazy='dynamic') 
    zans = db.relationship('Zan', backref='post', lazy='dynamic')
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))  

class Parent_child(db.Model):
    __tablename__ = 'parent_child'
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('comments.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
 
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
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
    float_id = db.Column(db.Integer, default='0')
    zans = db.relationship('Zan', backref='comment', lazy='dynamic')
    def relayedname(self, parent_childs):
        for parent_child in parent_childs:
            if parent_child.parent_id == self.post_id and parent_child.child_id == self.id:
                return self.post.author.username
            if parent_child.parent_id != self.post_id and parent_child.child_id == self.id:
                for item in self.post.comments:
                    if parent_child.parent_id == item.id:
                        return item.author.username
          
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))
  
db.event.listen(Comment.body, 'set', Comment.on_changed_body)

class Zan(db.Model):
    __tablename__ = 'zans'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.Boolean)
    type = db.Column(db.String(64), index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))

