"""
学生成绩管理系统 - 应用工厂
"""
import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from config import Config
from app.models import db, User

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保目录存在
    for folder in [app.config['UPLOAD_FOLDER'], app.config['EXPORT_FOLDER'], app.config['BACKUP_FOLDER']]:
        os.makedirs(folder, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 注册蓝图
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.teacher import teacher_bp
    from app.student import student_bp
    from app.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(api_bp, url_prefix='/api')

    # 模板上下文
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models import Notification
        unread_notifs = []
        if current_user.is_authenticated:
            query = Notification.query
            if current_user.is_student:
                query = query.filter(or_(
                    Notification.target_role == 'all',
                    Notification.target_role == 'student'
                ))
            elif current_user.is_teacher:
                query = query.filter(or_(
                    Notification.target_role == 'all',
                    Notification.target_role == 'teacher'
                ))
            elif current_user.is_academic:
                query = query.filter(or_(
                    Notification.target_role == 'all',
                    Notification.target_role == 'academic'
                ))
            unread_notifs = query.order_by(Notification.created_at.desc()).limit(5).all()
        return dict(current_user=current_user, unread_notifs=unread_notifs)

    # 根路由
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.is_super_admin:
                return redirect(url_for('admin.dashboard'))
            elif current_user.is_teacher:
                return redirect(url_for('teacher.dashboard'))
            elif current_user.is_student:
                return redirect(url_for('student.dashboard'))
            elif current_user.is_academic:
                return redirect(url_for('admin.academic_dashboard'))
        return redirect(url_for('auth.login'))

    # 错误处理
    @app.errorhandler(403)
    def forbidden(e):
        return render_error(403, '权限不足', '您没有权限访问此页面')

    @app.errorhandler(404)
    def not_found(e):
        return render_error(404, '页面未找到', '您访问的页面不存在')

    @app.errorhandler(500)
    def server_error(e):
        return render_error(500, '服务器错误', '系统内部错误，请稍后重试')

    def render_error(code, title, msg):
        from flask import render_template
        return render_template('error.html', code=code, title=title, msg=msg), code

    return app


from sqlalchemy import or_
