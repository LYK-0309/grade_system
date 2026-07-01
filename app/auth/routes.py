"""
认证路由: 登录/登出/修改密码
"""
from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, LoginLog
from app.utils import log_login, log_operation
from datetime import datetime

from app.auth import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active_user:
                flash('账号已被禁用，请联系管理员', 'danger')
                log_login(user, 'fail', '账号已禁用')
                return render_template('auth/login.html')
            login_user(user, remember=request.form.get('remember'))
            user.last_login = datetime.now()
            db.session.commit()
            log_login(user, 'login', '登录成功')
            flash(f'欢迎回来，{user.name}！', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            log_login(user, 'fail', f'用户名或密码错误: {username}')
            flash('用户名或密码错误', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log_login(current_user, 'logout', '退出登录')
    logout_user()
    flash('已安全退出', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pwd = request.form.get('old_password', '')
        new_pwd = request.form.get('new_password', '')
        confirm_pwd = request.form.get('confirm_password', '')
        if not current_user.check_password(old_pwd):
            flash('原密码错误', 'danger')
        elif len(new_pwd) < 6:
            flash('新密码至少6位', 'danger')
        elif new_pwd != confirm_pwd:
            flash('两次密码不一致', 'danger')
        else:
            current_user.set_password(new_pwd)
            db.session.commit()
            log_operation('update', '修改密码', f'用户 {current_user.username} 修改了密码')
            flash('密码修改成功', 'success')
            return redirect(url_for('index'))
    return render_template('auth/change_password.html')
