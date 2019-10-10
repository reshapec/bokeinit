#!/usr/bin/python3

"""主蓝本中定义的应用路由"""

from datetime import datetime 
from flask import render_template, session, redirect, url_for, flash, jsonify, request, make_response
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm, ReplyForm
from .. import db
from ..models import User, Role, Permission, Post, Follow, Comment, Parent_child, Zan
from flask_login import login_required, current_user
from ..decorators import admin_required, permission_required
from werkzeug.utils import secure_filename
import os
from PIL import Image
from flask import send_file, send_from_directory 

@main.route('/write_post', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.WRITE)
def write_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.body.data, 
                    author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('main/post_form.html', form=form)

@main.route('/', methods=['GET', 'POST'])
def index():
    page = request.args.get('page', 1, type=int) 
    show_idols = False
    if current_user.is_authenticated:
        show_idols = bool(request.cookies.get('show_idols', ''))
    if show_idols:
        query = current_user.idols_posts
    else: 
        query = Post.query 
    pagination = query.order_by(Post.timestamp.desc()).paginate(page, per_page=5, error_out=False)
    posts = pagination.items 
    return render_template('main/index.html', posts=posts, pagination=pagination, show_idols=show_idols)

@main.route('/all')
@login_required
def show_all():
    response = make_response(redirect(url_for('main.index')))
    response.set_cookie('show_idols', '', max_age=30*24*60*60)
    return response

@main.route('/idols')
@login_required
def show_idols():
    response = make_response(redirect(url_for('main.index')))
    response.set_cookie('show_idols', '1', max_age=30*24*60*60)
    return response

@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first()
    if user:
        return render_template('main/user.html', user=user)
    if user is None:
        return render_template('main/404.html'), 404

@main.route('/<username>/posts/')
@login_required
def posts(username):
    user = User.query.filter_by(username=username).first()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.top.desc(), Post.timestamp.desc()).paginate(page, per_page=5, error_out=False)
    posts = pagination.items
    num = len(list(user.posts))
    return render_template('main/username_posts.html', user=user, posts=posts, pagination=pagination, num=num)

@main.route('/post/<int:id>', methods=['GET', 'POST'])
@login_required
def post(id):
    post = Post.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // 5 + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(page, per_page=5,
error_out=False)
    comments = pagination.items
    num = post.comments.count()
    parent_childs = Parent_child.query.all()
    return render_template('main/post.html', posts=[post], comments=comments, pagination=pagination, num=num, parent_childs=parent_childs)

@main.route('/comment/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.COMMENT)
def comment(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        parent_child = Parent_child(parent_id=post.id, child_id=comment.id)
        db.session.add(parent_child)
        db.session.commit()
        i = post.comments.count()
        if i > 0:
            item = post.comments.order_by(Comment.timestamp.asc()).all()[i-1]
            item.float_id += post.comments.count()
            db.session.add(item)
            db.session.commit()
        return redirect(url_for('main.post', id=post.id))
    return render_template('main/comment_form.html', form=form)

@main.route('/commenttocomment/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.COMMENT)
def commenttocomment(id):
    parent_comment = Comment.query.get_or_404(id)
    post = parent_comment.post
    form = CommentForm()
    if form.validate_on_submit():
        child_comment = Comment(body=form.body.data,
                                post=post,
                                author=current_user._get_current_object())
        db.session.add(child_comment)
        db.session.commit()
        parent_child = Parent_child(parent_id=parent_comment.id, 
                                    child_id=child_comment.id)
        db.session.add(parent_child)
        db.session.commit()
        i = post.comments.count()
        if i > 0:
            item = post.comments.order_by(Comment.timestamp.asc()).all()[i-1]
            item.float_id += post.comments.count()
            db.session.add(item)
            db.session.commit()
        return redirect(url_for('main.post', id=post.id))
    return render_template('main/comment_form.html', form=form)

@main.route('/cancelcomment/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.COMMENT)
def cancelcomment(id):
    comment = Comment.query.get_or_404(id)
    post = comment.post
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('main.post', id=post.id))
   
@main.route('/zanpost/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ZAN)
def zanpost(id):
    post = Post.query.get_or_404(id)
    zans = Zan.query.filter_by(post_id=post.id).all()
    no_zan = 0
    if zans:
        for zan in zans:
            if zan.author != current_user:
                no_zan += 1
            else:
                no_zan += 0
        if len(zans) == no_zan:
            item = Zan(author=current_user._get_current_object(),
                       status=True, 
                       type='post',
                       post=post)
            db.session.add(item)
            db.session.commit()
        flash('您已点赞该博客')
    else:
        item = Zan(author=current_user._get_current_object(),
                   status=True,
                   type='post',
                   post=post)
        db.session.add(item)
        db.session.commit()
        flash('您已点赞该博客')
    return redirect(url_for('main.post', id=post.id))

@main.route('/cancelzanpost/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ZAN)
def cancelzanpost(id):
    post = Post.query.get_or_404(id)
    zans = Zan.query.filter_by(post_id=post.id).all()
    for zan in zans:
        if zan.author == current_user:
            db.session.delete(zan)
            db.session.commit()
    flash('您已取消对该博客的赞')
    return redirect(url_for('main.post', id=post.id))
  
@main.route('/zancomment/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ZAN)
def zancomment(id):
    comment = Comment.query.get_or_404(id)
    zans = Zan.query.filter_by(comment_id=comment.id).all()
    no_zan = 0
    if zans:
        for zan in zans:
            if zan.author != current_user:
                no_zan += 1
            else:
                no_zan += 0
        if len(zans) == no_zan:
            item = Zan(author=current_user._get_current_object(),
                       status=True, 
                       type='comment',
                       comment=comment)
            db.session.add(item)
            db.session.commit()
        flash('您已点赞该评论')
    else:
        item = Zan(author=current_user._get_current_object(),
                   status=True,
                   type='comment',
                   comment=comment)
        db.session.add(item)
        db.session.commit()
        flash('您已点赞该评论')
    return redirect(url_for('main.post', id=comment.post.id))

@main.route('/cancelzancomment/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ZAN)
def cancelzancomment(id):
    comment = Comment.query.get_or_404(id)
    zans = Zan.query.filter_by(comment_id=comment.id).all()
    for zan in zans:
        if zan.author == current_user:
            db.session.delete(zan)
            db.session.commit()
    flash('您已取消对该评论的赞')
    return redirect(url_for('main.post', id=comment.post.id))

@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        return render_template('main/403.html')
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash('该帖子已更新')
        return redirect(url_for('main.post', id=post.id))
    form.body.data = post.body
    return render_template('main/edit.html', form=form)

@main.route('/<username>/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(username, id):
    user = User.query.filter_by(username=username).first()
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        return render_template('main/403.html')
    db.session.delete(post)
    db.session.commit()
    flash('该帖已删除')
    return redirect(url_for('main.posts', username=post.author.username))

@main.route('/<username>/istop/<int:id>', methods=['GET', 'POST'])
@login_required
def istop(username, id):
    user = User.query.filter_by(username=username).first()
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        return render_template('main/403.html')
    post.top = 1
    db.session.add(post)
    db.session.commit()
    flash('文章已置顶')
    return redirect(url_for('main.posts', username=post.author.username))

@main.route('/<username>/notop/<int:id>', methods=['GET', 'POST'])
@login_required
def notop(username, id):
    user = User.query.filter_by(username=username).first()
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        return render_template('main/403.html')
    post.top = 0
    db.session.add(post)
    db.session.commit()
    flash('文章已取消置顶')
    return redirect(url_for('main.posts', username=post.author.username))

@main.route('/show_reading/<int:id>')
def show_reading(id):
    response = make_response(redirect(url_for('main.post', id=id)))
    response.set_cookie('readings', '1', max_age=24*60*60)
    return response

@main.route('/follow/<username>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('main.index'))
    if current_user.is_following(user):
        flash('您已经关注该用户')
        return redirect(url_for('main.user', username=user.username))
    current_user.follow(user)
    db.session.commit()
    return redirect(url_for('main.user', username=user.username))

@main.route('/unfollow/<username>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效用户')
        return redirect(url_for('main.index'))
    if current_user.is_following(user):
        current_user.unfollow(user)
        db.session.commit()
        return redirect(url_for('main.user', username=user.username))

@main.route('/fans/<username>')
def fans(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效用户')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(page, per_page=10, error_out=False)
    fans = [] 
    for item in pagination.items:
        fan = {'user': item.follower, 'timestamp': item.timestamp}
        fans.append(fan)    
    return render_template('main/fans.html', user=user, title="粉丝",
                           endpoint='main.fans', pagination=pagination,
                           fans=fans)

@main.route('/idols/<username>')
def idols(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效用户')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(page, per_page=10, error_out=False)
    idols = []
    for item in pagination.items:
        idol = {'user': item.followed, 'timestamp': item.timestamp}
        idols.append(idol)
    return render_template('main/idols.html', user=user, title="关注",
                           endpoint='main.idols', pagination=pagination,
                           idols=idols)

@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(page, per_page=10, error_out=False)
    comments = pagination.items
    return render_template('main/moderate.html', comments=comments, pagination=pagination, page=page)

@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.moderate', page=request.args.get('page', 1, type=int)))

@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.moderate', page=request.args.get('page', 1, type=int)))

@main.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        db.session.commit()
        flash('您的个人资料已更新')
        return redirect(url_for('main.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('main/edit_profile.html', form=form)

@main.route('/edit_profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('该用户个人资料已更新')
        return redirect(url_for('main.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('main/edit_profile.html', form=form, user=user)


ALLOWED_EXTENSIONS=set(['txt','pdf','png','jpg','jpeg','gif'])
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) 
UPLOAD_FOLDER = os.path.join(basedir, 'static/images')
DOWNLOAD_FOLDER = os.path.join(basedir, 'static/documents')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@main.route('/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        im = Image.open(file)
        im.thumbnail((200, 200))
        im_2 = Image.open(file)
        im_2.thumbnail((40, 40))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            im.save(os.path.join(UPLOAD_FOLDER, filename))
            im_2.save(os.path.join(UPLOAD_FOLDER, str(2) + filename))
            current_user.avatar_hash = 'images/' + filename
            current_user.avatar_hash_2 = 'images/' + str(2) + filename
            db.session.commit()
            return redirect(url_for('main.user', username=current_user.username))
        else:
            return '<p>上传了不被允许的类型</p>'
    return render_template('main/upload_file.html')


@main.route('/download/<filename>', methods=['GET'])
@login_required
def download(filename):
    response = make_response(send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True))
    response.headers["Content-Disposition"] = "attachment; filename={}".format(filename.encode().decode('latin-1'))
    return response

@main.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        keywords = request.form['searchwords']
        posts = Post.query.order_by(Post.timestamp.desc()).all()
        results = []
        for post in posts:
            if keywords in post.body:
               results.append(post)
        if len(results) == 0:
            status = "error"
        else:
            status = "success"
        counts = len(results)
        return render_template('main/search_results.html', keywords=keywords, results=results, status=status, counts=counts)
    return render_template('main/search.html')

@main.route('/video')
def video():
    return render_template('main/video.html')

@main.route('/display_document')
def display_document():
    return render_template('main/display_document.html')

