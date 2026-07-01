"""
学生成绩管理系统 - 数据模型
角色: super_admin(超管) / teacher(教师) / student(学生) / academic(教务)
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, and_, or_

db = SQLAlchemy()


# ── 用户与权限 ──────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # super_admin/teacher/student/academic
    name = db.Column(db.String(64), nullable=False)
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)

    # 关联
    teacher = db.relationship('Teacher', backref='user', uselist=False)
    student = db.relationship('Student', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    @property
    def is_teacher(self):
        return self.role == 'teacher'

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_academic(self):
        return self.role == 'academic'

    @property
    def role_name(self):
        return {'super_admin': '超级管理员', 'teacher': '教师', 'student': '学生', 'academic': '教务管理员'}.get(self.role, '未知')

    @property
    def is_active(self):
        return self.is_active_user


class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(64))
    ip = db.Column(db.String(64))
    action = db.Column(db.String(20))  # login/logout/fail
    detail = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.now)


class OperationLog(db.Model):
    __tablename__ = 'operation_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(64))
    action = db.Column(db.String(64))   # create/update/delete/export/import
    target = db.Column(db.String(128))  # 操作对象描述
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


# ── 基础信息 ──────────────────────────────────────────
class ClassInfo(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    grade = db.Column(db.String(32))      # 年级 如 23本
    major = db.Column(db.String(128))     # 专业
    duration = db.Column(db.String(32))   # 学制 如 4年
    created_at = db.Column(db.DateTime, default=datetime.now)

    students = db.relationship('Student', backref='class_info', lazy='dynamic')
    courses = db.relationship('Course', backref='class_info', lazy='dynamic')


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column(db.String(32), unique=True, nullable=False, index=True)  # 学号
    name = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(4))  # 男/女
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    enrollment_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='正常')  # 正常/休学/退学
    college = db.Column(db.String(128))  # 院系
    major = db.Column(db.String(128))    # 专业
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 关联用户账号
    created_at = db.Column(db.DateTime, default=datetime.now)

    grades = db.relationship('Grade', backref='student', lazy='dynamic')

    @property
    def status_badge(self):
        return {'正常': 'success', '休学': 'warning', '退学': 'danger'}.get(self.status, 'secondary')


class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    teacher_no = db.Column(db.String(32), unique=True, nullable=False, index=True)  # 工号
    name = db.Column(db.String(64), nullable=False)
    department = db.Column(db.String(128))  # 院系
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 关联用户账号
    created_at = db.Column(db.DateTime, default=datetime.now)

    courses = db.relationship('Course', backref='teacher', lazy='dynamic')


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(32), unique=True, nullable=False, index=True)  # 课程编号
    name = db.Column(db.String(128), nullable=False)
    credit = db.Column(db.Float, default=2.0)   # 学分
    hours = db.Column(db.Integer, default=32)   # 课时
    assessment_type = db.Column(db.String(20), default='考查')  # 考试/考查
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    semester = db.Column(db.String(32), default='2025-2026-2')  # 学期
    is_locked = db.Column(db.Boolean, default=False)  # 成绩锁定
    created_at = db.Column(db.DateTime, default=datetime.now)

    grades = db.relationship('Grade', backref='course', lazy='dynamic')

    @property
    def assessment_badge(self):
        return 'primary' if self.assessment_type == '考试' else 'info'


# ── 成绩核心 ──────────────────────────────────────────
class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    score = db.Column(db.Float)  # 综合成绩 (0~100 或 None 表示缺考)
    # 成绩组成 (可选)
    score_discuss = db.Column(db.Float)       # 讨论
    score_homework = db.Column(db.Float)      # 作业
    score_attendance = db.Column(db.Float)    # 签到
    score_points = db.Column(db.Float)        # 课程积分
    score_pbl = db.Column(db.Float)           # 分组任务PBL
    # 特殊标记
    special_mark = db.Column(db.String(20))   # null/缺考/作弊/缓考
    # 考试批次
    exam_type = db.Column(db.String(20), default='期末')  # 期中/期末/补考/重修
    # 绩点
    gpa = db.Column(db.Float)
    # 状态
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', 'exam_type'),)

    @property
    def score_display(self):
        if self.special_mark in ('缺考', '作弊', '缓考'):
            return self.special_mark
        if self.score is None:
            return '-'
        return f'{self.score:.2f}'

    @property
    def grade_level(self):
        """等级制 A/B/C/D"""
        if self.special_mark in ('缺考', '作弊'):
            return 'F'
        if self.score is None:
            return '-'
        if self.score >= 90:
            return 'A'
        elif self.score >= 80:
            return 'B'
        elif self.score >= 70:
            return 'C'
        elif self.score >= 60:
            return 'D'
        else:
            return 'F'

    @property
    def is_pass(self):
        if self.special_mark in ('缺考', '作弊'):
            return False
        if self.score is None:
            return False
        return self.score >= 60

    @staticmethod
    def calc_gpa(score, special_mark=None):
        """绩点换算: 90-100=4.0, 85-89=3.7, 82-84=3.3, 78-81=3.0, 75-77=2.7, 72-74=2.3, 68-71=2.0, 64-67=1.5, 60-63=1.0, <60=0"""
        if special_mark in ('缺考', '作弊') or score is None or score < 60:
            return 0.0
        if score >= 90:
            return 4.0
        elif score >= 85:
            return 3.7
        elif score >= 82:
            return 3.3
        elif score >= 78:
            return 3.0
        elif score >= 75:
            return 2.7
        elif score >= 72:
            return 2.3
        elif score >= 68:
            return 2.0
        elif score >= 64:
            return 1.5
        else:
            return 1.0


class GradeRevision(db.Model):
    """成绩修改记录"""
    __tablename__ = 'grade_revisions'
    id = db.Column(db.Integer, primary_key=True)
    grade_id = db.Column(db.Integer, db.ForeignKey('grades.id'), nullable=False)
    original_score = db.Column(db.Float)
    new_score = db.Column(db.Float)
    original_special = db.Column(db.String(20))
    new_special = db.Column(db.String(20))
    modified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    modifier_name = db.Column(db.String(64))
    reason = db.Column(db.String(256))
    status = db.Column(db.String(20), default='pending')  # pending/approved/rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    grade = db.relationship('Grade', backref='revisions')


# ── 辅助 ──────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text)
    target_role = db.Column(db.String(20))  # all/teacher/student/academic
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_pinned = db.Column(db.Boolean, default=False)


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.String(256))
    description = db.Column(db.String(128))
