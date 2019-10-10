#!/usr/bin/python3

"""主蓝本中定义的应用路由"""
# url_for('命名空间.端点名')，命名空间即蓝本名称(Blueprint构造函数的第一个参数),端点名即视图函数名称

from datetime import datetime # 添加一个datetime变量
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
from flask import send_file, send_from_directory # 文件下载，接口返回真实的文件

# 路由装饰器由蓝本提供，因此使用main.route, 而非app.route
# Flask_Login提供了一个login_required装饰器，如果未通过身份验证的用户访问这个路由，Flask_Login将拦截请求，把用户发往登录页面
# current_user由flask_login提供，与所有的上下文变量一样，也是实现为线程内的代理对象，这个对象的表现类似于用户对象，但实际上却是一个轻度包装，包含真正的用户对象，数据库需要真正的用户对象，因此需要在代理对象上调用_get_current_object()方法

# 写博客的路由
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
        return redirect(url_for('main.index')) # 写完博客推至数据库后重定向到首页
    return render_template('main/post_form.html', form=form)

# 处理博客文章的首页路由,支持:分页显示数据，分段渲染
@main.route('/', methods=['GET', 'POST'])
def index():
    # args是MultiDict字典，它的get()方法是: get(key, default=None, type=None), 通过第三个参数设置的类型，将第一个参数取到的值转化成该类型，如果转换失败，则返回默认值
    page = request.args.get('page', 1, type=int) 
    """显示所有博客文章或只显示所关注用户的文章"""
    show_idols = False
    if current_user.is_authenticated:
        show_idols = bool(request.cookies.get('show_idols', ''))
    if show_idols: # show_idols为非空字符串
        query = current_user.idols_posts # 获取过滤后的博客文章查询
    else: # show_idols为空字符串
        query = Post.query # 使用顶级查询Post.query，获得所有用户的文章
    # 对时间戳降序, 调用paginate()方法返回一个Pagination对象，包含指定范围内的结果;页数、每页显示的记录数量、页数超过范围时返回一个空列表
    pagination = query.order_by(Post.timestamp.desc()).paginate(page, per_page=5, error_out=False)
    posts = pagination.items # 分页对象的当前页面中的记录
    return render_template('main/index.html', posts=posts, pagination=pagination, show_idols=show_idols)

# 查询所有文章还是所关注用户的文章
@main.route('/all')
@login_required
def show_all():
    response = make_response(redirect(url_for('main.index')))
    response.set_cookie('show_idols', '', max_age=30*24*60*60) # 30天
    return response

@main.route('/idols')
@login_required
def show_idols():
    response = make_response(redirect(url_for('main.index')))
    response.set_cookie('show_idols', '1', max_age=30*24*60*60) # 30天
    return response

# 用户的资料页面动态路由
@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first()
    if user:
        return render_template('main/user.html', user=user)
    if user is None:
        return render_template('main/404.html'), 404

# 分解用户的资料页面动态路由，点击资料页面'xx的文章'链接，导航至新页面，支持:分页显示数据，分段渲染(自己写的)
@main.route('/<username>/posts/')
@login_required
def posts(username):
    user = User.query.filter_by(username=username).first()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.top.desc(), Post.timestamp.desc()).paginate(page, per_page=5, error_out=False)
    posts = pagination.items
    num = len(list(user.posts))
    # 分页显示数据，分段渲染用户的所有博客
    return render_template('main/username_posts.html', user=user, posts=posts, pagination=pagination, num=num)

# 1.查看单条博客的固定链接, html页面显示：单条博客、在这条博客下的所有评论(包括1.1和1.2)、在这条博客下的所有赞取消(包括1.3和1.4)、分页显示、用cookie统计单条博客的阅读量
@main.route('/post/<int:id>', methods=['GET', 'POST'])
@login_required
def post(id):
    post = Post.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    # 从查询字符串中获取页数，值为-1时
    if page == -1:
        # 计算总评论数和总页数，得出评论的最后一页的页数
        page = (post.comments.count() - 1) // 5 + 1
    # 分页对象
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(page, per_page=5,
error_out=False)
    # 分页对象当前页面中的评论记录
    comments = pagination.items
    num = post.comments.count()
    # 父子表
    parent_childs = Parent_child.query.all()
    return render_template('main/post.html', posts=[post], comments=comments, pagination=pagination, num=num, parent_childs=parent_childs)

# 1.1 针对博客的评论(自己写的)
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
        # 添加父子关系
        parent_child = Parent_child(parent_id=post.id, child_id=comment.id)
        db.session.add(parent_child)
        db.session.commit()
        # 仿贴吧楼层，对指定博客的所有评论内容顺序排序,不重复计算已有楼层数
        i = post.comments.count()
        if i > 0:
            item = post.comments.order_by(Comment.timestamp.asc()).all()[i-1]
            item.float_id += post.comments.count()
            db.session.add(item)
            db.session.commit()
        return redirect(url_for('main.post', id=post.id))
    return render_template('main/comment_form.html', form=form)

# 1.2 针对评论的评论(自己写的)
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
        # 添加父子关系
        parent_child = Parent_child(parent_id=parent_comment.id, 
                                    child_id=child_comment.id)
        db.session.add(parent_child)
        db.session.commit()
        # 仿贴吧楼层，对指定博客的所有评论内容顺序排序,不重复计算已有楼层数
        i = post.comments.count()
        if i > 0:
            item = post.comments.order_by(Comment.timestamp.asc()).all()[i-1]
            item.float_id += post.comments.count()
            db.session.add(item)
            db.session.commit()
        return redirect(url_for('main.post', id=post.id))
    return render_template('main/comment_form.html', form=form)

# 删除评论的路由(自己写的)
@main.route('/cancelcomment/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.COMMENT)
def cancelcomment(id):
    comment = Comment.query.get_or_404(id)
    post = comment.post
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('main.post', id=post.id))
   
# 1.4.1 点赞博客的路由(自己写的)
@main.route('/zanpost/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ZAN)
def zanpost(id):
    post = Post.query.get_or_404(id)
    # 在数据库中查找关于本博客的点赞表
    zans = Zan.query.filter_by(post_id=post.id).all()
    no_zan = 0
    # 点赞表存在，遍历点赞表，在当前用户没有给博客点赞的情况下，添加点赞记录
    if zans:
        for zan in zans:
            if zan.author != current_user:
                no_zan += 1
            else:
                no_zan += 0
        # 点赞记录的长度等于未赞数量时，即现有的点赞记录不存在当前用户的点赞，则新增
        if len(zans) == no_zan:
            item = Zan(author=current_user._get_current_object(),
                       status=True, 
                       type='post',
                       post=post)
            db.session.add(item)
            db.session.commit()
        flash('您已点赞该博客')
    # 点赞表不存在，即该博客尚未获得任何赞，新增来自当前用户的点赞记录
    else:
        item = Zan(author=current_user._get_current_object(),
                   status=True,
                   type='post',
                   post=post)
        db.session.add(item)
        db.session.commit()
        flash('您已点赞该博客')
    return redirect(url_for('main.post', id=post.id))

# 1.4.2 取消赞博客的路由(自己写的)
@main.route('/cancelzanpost/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ZAN)
def cancelzanpost(id):
    post = Post.query.get_or_404(id)
    zans = Zan.query.filter_by(post_id=post.id).all()
    for zan in zans:
        # 遍历点赞表，如果当前用户已点赞博客，删除点赞，再推送至数据库
        if zan.author == current_user:
            db.session.delete(zan)
            db.session.commit()
    flash('您已取消对该博客的赞')
    return redirect(url_for('main.post', id=post.id))
  
# 1.5.1 点赞评论的路由(自己写的)   
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

# 1.5.2 取消赞评论的路由(自己写的)
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

# 2.编辑单条博客内容的路由
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

# 3.删除单条博客所有信息的路由---(自己写的)
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

# 4.实现博客置顶功能的路由---(自己写的)
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

# 5.取消置顶博客的路由---(自己写的)
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

# 6. 查看单条博客阅读量的路由(自己写的,坑待填，不完整)
@main.route('/show_reading/<int:id>')
def show_reading(id):
    response = make_response(redirect(url_for('main.post', id=id))) # 设置响应对象
    response.set_cookie('readings', '1', max_age=24*60*60) # 设置cookie的过期时间: 1天
    return response # 为readings cookie设定适当的值后，重定向到单条博客页面

# 关注路由
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
    #flash('您现在关注 %s' % username)
    return redirect(url_for('main.user', username=user.username))

# 取消关注路由
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
        #flash('您已取消关注 %s' % username)
        return redirect(url_for('main.user', username=user.username))

# 粉丝路由
@main.route('/fans/<username>')
def fans(username):
    user = User.query.filter_by(username=username).first()
    # 判断用户是否存在
    if user is None:
        flash('无效用户')
        return redirect(url_for('main.index'))
    # 当用户存在时，分页显示用户的粉丝(10个/页)
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(page, per_page=10, error_out=False)
    # 空列表
    fans = [] 
    # 遍历分页对象当前页面中的记录(item是Follow模型的实例)
    for item in pagination.items:
        # 给粉丝字典的键赋值
        fan = {'user': item.follower, 'timestamp': item.timestamp}
        # fans是一个字典列表, 粉丝列表
        fans.append(fan)    
    # followers.html模板接收的参数包括用户对象、页面标题、分页链接使用的端点、分页对象、查询结果列表
    return render_template('main/fans.html', user=user, title="粉丝",
                           endpoint='main.fans', pagination=pagination,
                           fans=fans)

# 关注路由
@main.route('/idols/<username>')
def idols(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效用户')
        return redirect(url_for('main.index'))
    # 当用户存在时，分页显示用户的已经关注的人(10个/页)
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(page, per_page=10, error_out=False)
    idols = []
    for item in pagination.items:
        idol = {'user': item.followed, 'timestamp': item.timestamp}
        idols.append(idol)
    return render_template('main/idols.html', user=user, title="关注",
                           endpoint='main.idols', pagination=pagination,
                           idols=idols)

# 管理评论路由
@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(page, per_page=10, error_out=False)
    comments = pagination.items
    return render_template('main/moderate.html', comments=comments, pagination=pagination, page=page)

# 开放评论路由
@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.moderate', page=request.args.get('page', 1, type=int)))

# 禁用评论路由
@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.moderate', page=request.args.get('page', 1, type=int)))

# 普通用户的资料编辑路由
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

# 管理员的资料编辑路由
@main.route('/edit_profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    # get_or_404() 返回指定主键对应的行，如果没有找到指定的主键，则终止请求，返回404错误响应
    # id是User模型的主键
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        # 表单提交后，id从字段的data属性中提取，并且查询时会使用提取出来的id值加载角色对象
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
    #设定字段初始值时，role_id被赋值给form.role.data，因为choices属性中设置的元组列表使用数字标识符表示各选项
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('main/edit_profile.html', form=form, user=user)


ALLOWED_EXTENSIONS=set(['txt','pdf','png','jpg','jpeg','gif']) # 设置允许的文件格式
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) 
UPLOAD_FOLDER = os.path.join(basedir, 'static/images') # 上传文件的存放路径
DOWNLOAD_FOLDER = os.path.join(basedir, 'static/documents') # 下载文件的下载路径

# 检查上传的文件的后缀名是否属于允许的文件格式
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# 上传文件的路由(自己写的)
@main.route('/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        """从request请求的files字典中，取出file对应的文件，文件是一个
      FileStorage对象,该对象的save()函数保存文件,该对象的filename属性提取文件名，参数是路径名称。示范: file.save(os.path.join(UPLOAD_FOLDER, file.filename)) """
        file = request.files['file']
        # 创建缩略图
        im = Image.open(file)
        im.thumbnail((200, 200))
        im_2 = Image.open(file)
        im_2.thumbnail((40, 40))
        # 文件存在且后缀名正确情况下
        if file and allowed_file(file.filename):
            # secure_filename()函数，处理提取的文件名(把文件名里面的斜杠和空格，替换成了下划线, 保证了文件只会在当前目录使用，而不会由于路径问题被利用去做其他事情)
            filename = secure_filename(file.filename)
            # 将缩略图保存到项目静态文件static下的指定目录
            im.save(os.path.join(UPLOAD_FOLDER, filename))
            im_2.save(os.path.join(UPLOAD_FOLDER, str(2) + filename))
            # 将图片路径保存至数据库
            current_user.avatar_hash = 'images/' + filename
            current_user.avatar_hash_2 = 'images/' + str(2) + filename
            db.session.commit()
            return redirect(url_for('main.user', username=current_user.username))
        else:
            return '<p>上传了不被允许的类型</p>'
    return render_template('main/upload_file.html')

# 下载文件的路由(自己写的)
@main.route('/download/<filename>', methods=['GET'])
@login_required
def download(filename):
    # 需要知道2个参数, 第1个参数是本地目录的path, 第2个参数是文件名(带扩展名)
    # 使用make_response函数建立一个response对象，然后将filename编码转为latin-1，可以看到server.py里边会严格按照latin-1编码来解析filename，这里的做法是先将utf8编码的中文文件名默认转为latin-1编码
    response = make_response(send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True))
    response.headers["Content-Disposition"] = "attachment; filename={}".format(filename.encode().decode('latin-1'))
    return response

# 实现站内搜索功能的路由(自己写的)
@main.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        # 表单数据由Web浏览器提交给服务器，对包含表单数据的POST请求来说，用户填写的信息通过request.form访问
        # request.form字典，存储请求提交的所有表单字段，后端通过form的name标识来获取前端传递过来的关键字
        # form表单，会将它的输入框中的值，绑定到'name'属性中，后端取值的时候也是根据'name'属性的值去取值
        keywords = request.form['searchwords']
        # 取出数据库中的所有博客，时间倒序排列
        posts = Post.query.order_by(Post.timestamp.desc()).all()
        # 空列表，存放符合条件的博客
        results = []
        # 遍历所有博客，如果在博客的主体中存在关键字，将博客存入上述列表
        for post in posts:
            if keywords in post.body:
               results.append(post)
        # 列表为空，状态为"error"; 否则为"success"
        if len(results) == 0:
            status = "error"
        else:
            status = "success"
        # 计算列表长度，即为检索出的包含关键字的博客条数
        counts = len(results)
        return render_template('main/search_results.html', keywords=keywords, results=results, status=status, counts=counts)
    return render_template('main/search.html')

# 视频区(自己写的，游客可以观看视频区的内容，未加@login_required装饰器)
@main.route('/video')
def video():
    return render_template('main/video.html')

# 资料区(自己写的，游客可以观看资料区的内容，未加login_required装饰器，但是想要下载文件就会被发往登录页面--- 下载文件的路由被加了login_required装饰器)
@main.route('/display_document')
def display_document():
    return render_template('main/display_document.html')


"""
# 从指定的URL中下载JSON格式的数据(有用)
import requests
json_url = 'https://raw.githubusercontent.com/muxuezi/btc/master/btc_close_2017.json'
# requests通过get方法向指定服务器发送请求，服务器响应请求后，返回的结果存储在req变量中
req = requests.get(json_url)
# 将数据写入文件
with open('btc_close_2017_request.json', 'w') as f:
    f.write(req.text) # req.text属性可以直接读取文件数据

# 回复评论路由--(只有一层结构，不成功，已经使用自引用关系实现回复功能)
@main.route('/reply/<int:id>', methods=['GET', 'POST'])
def reply(id):
    comment = Comment.query.get_or_404(id)
    form = ReplyForm()
    if form.validate_on_submit():
        reply = Reply(body=form.body.data,
                      comment=comment,
                      author=current_user._get_current_object())
        db.session.add(reply)
        db.session.commit()
    replys = comment.replys.order_by(Reply.timestamp.asc()).all()
    return render_template('main/reply.html', form=form, replys=replys, comment=comment)

# 1.提供博客文章的固定链接, 支持博客文章评论--(改进，1、将发表评论的表单和post.html页面分开; 2、把提交评论至数据库的动作和post.html页面分开，点击链接跳转至表单页面，提交数据库后再重定向到post.html页面，利于发表针对博客的评论和针对评论的评论，两类发表使用同种表单 )
@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        # url_for()函数中的参数把page设为-1, 用于请求评论的最后一页
        return redirect(url_for('main.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    # 从查询字符串中获取页数，值为-1时
    if page == -1:
        # 计算总评论数和总页数，得出评论的最后一页的页数
        page = (post.comments.count() - 1) // 5 + 1
    # 分页对象
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(page, per_page=5, error_out=False)
    # 分页对象当前页面中的评论记录
    comments = pagination.items
    num = post.comments.count()
    return render_template('main/post.html', posts=[post], form=form, comments=comments, pagination=pagination, num=num)
"""#
