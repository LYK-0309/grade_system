"""
API路由: 图表数据/模糊检索/通知
"""
from flask import jsonify, request
from flask_login import login_required, current_user
from app.models import db, Student, Course, Grade, ClassInfo, Notification
from app.utils import (role_required, teacher_or_admin, calc_class_stats,
                       calc_grade_distribution)
from sqlalchemy import or_

from app.api import api_bp


@api_bp.route('/stats/course/<int:course_id>')
@login_required
@teacher_or_admin
def course_stats_api(course_id):
    """课程统计API (用于图表)"""
    exam_type = request.args.get('exam_type', '期末')
    grades = Grade.query.filter_by(course_id=course_id, exam_type=exam_type).all()
    stats = calc_class_stats(grades)
    dist = calc_grade_distribution(grades)
    return jsonify({
        'stats': stats,
        'distribution': dist,
        'labels': list(dist.keys()),
        'values': list(dist.values()),
    })


@api_bp.route('/stats/class/<int:class_id>')
@login_required
@role_required('super_admin', 'academic', 'teacher')
def class_stats_api(class_id):
    """班级统计API"""
    grades = Grade.query.join(Student).filter(
        Student.class_id == class_id, Grade.exam_type == '期末'
    ).all()
    stats = calc_class_stats(grades)
    dist = calc_grade_distribution(grades)
    return jsonify({
        'stats': stats,
        'distribution': dist,
        'labels': list(dist.keys()),
        'values': list(dist.values()),
    })


@api_bp.route('/search/students')
@login_required
@role_required('super_admin', 'academic', 'teacher')
def search_students():
    """模糊搜索学生"""
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify([])
    students = Student.query.filter(
        or_(Student.name.contains(q), Student.student_no.contains(q))
    ).limit(20).all()
    return jsonify([{
        'id': s.id,
        'student_no': s.student_no,
        'name': s.name,
        'class': s.class_info.name if s.class_info else '',
        'status': s.status,
    } for s in students])


@api_bp.route('/search/courses')
@login_required
@teacher_or_admin
def search_courses():
    """模糊搜索课程"""
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify([])
    courses = Course.query.filter(
        or_(Course.name.contains(q), Course.course_code.contains(q))
    ).limit(20).all()
    return jsonify([{
        'id': c.id,
        'code': c.course_code,
        'name': c.name,
        'teacher': c.teacher.name if c.teacher else '',
    } for c in courses])


@api_bp.route('/notifications/<int:nid>/read')
@login_required
def mark_notification_read(nid):
    """标记通知已读 (前端模拟)"""
    return jsonify({'status': 'ok'})


@api_bp.route('/fail_list/<int:course_id>')
@login_required
@role_required('super_admin', 'academic', 'teacher')
def fail_list_api(course_id):
    """挂科名单API"""
    exam_type = request.args.get('exam_type', '期末')
    grades = Grade.query.filter_by(course_id=course_id, exam_type=exam_type).all()
    fail_grades = [g for g in grades if not g.is_pass]
    return jsonify([{
        'student_no': g.student.student_no,
        'name': g.student.name,
        'score': g.score_display,
        'special': g.special_mark or '',
        'class': g.student.class_info.name if g.student.class_info else '',
    } for g in fail_grades])
