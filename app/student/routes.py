"""
学生路由: 仪表板/成绩查询/成绩单/排名/导出
"""
from flask import render_template, redirect, url_for, request, flash, send_file, abort
from flask_login import login_required, current_user
from app.models import db, Grade, Course, Student, Notification
from app.utils import role_required, log_operation, calc_class_stats, get_rankings, create_grade_export, export_to_bytes
from datetime import datetime
import io

from app.student import student_bp


@student_bp.route('/dashboard')
@login_required
@role_required('student', 'super_admin', 'academic')
def dashboard():
    """学生仪表板"""
    stu = current_user.student
    if not stu:
        return render_template('error.html', code=403, title='账号未关联学生信息', msg='当前账号没有关联学生档案，请联系管理员处理。'), 403


    grades = stu.grades.filter_by(exam_type='期末').all()
    stats = {
        'course_count': len(grades),
        'avg_score': 0,
        'total_gpa': 0,
        'fail_count': 0,
    }
    if grades:
        valid = [g for g in grades if g.special_mark not in ('缺考', '作弊') and g.score is not None]
        if valid:
            scores = [g.score for g in valid]
            stats['avg_score'] = round(sum(scores) / len(scores), 2)
            gpas = [g.gpa or 0 for g in valid]
            stats['total_gpa'] = round(sum(gpas) / len(gpas), 2)
        stats['fail_count'] = sum(1 for g in grades if not g.is_pass)

    notifs = Notification.query.filter(
        db.or_(Notification.target_role == 'all', Notification.target_role == 'student')
    ).order_by(Notification.created_at.desc()).limit(5).all()

    return render_template('student/dashboard.html', stu=stu, grades=grades, stats=stats, notifs=notifs)


@student_bp.route('/grades')
@login_required
@role_required('student', 'super_admin', 'academic')
def my_grades():
    """我的成绩"""
    stu = current_user.student
    if not stu:
        abort(404)
    exam_type = request.args.get('exam_type', '期末')
    grades = stu.grades.filter_by(exam_type=exam_type).all()
    all_exam_types = [r[0] for r in db.session.query(Grade.exam_type).filter_by(student_id=stu.id).distinct().all()]

    return render_template('student/my_grades.html', stu=stu, grades=grades,
                           exam_type=exam_type, exam_types=all_exam_types)


@student_bp.route('/transcript')
@login_required
@role_required('student', 'super_admin', 'academic')
def transcript():
    """个人成绩单"""
    stu = current_user.student
    if not stu:
        abort(404)
    grades = stu.grades.filter_by(exam_type='期末').all()

    # 计算排名 (每门课程)
    for g in grades:
        course_grades = Grade.query.filter_by(course_id=g.course_id, exam_type='期末').all()
        rankings = get_rankings(course_grades)
        g._rank = rankings.get(g.student_id, '-')
        g._total = len(course_grades)

    # 总GPA
    valid = [g for g in grades if g.special_mark not in ('缺考', '作弊') and g.score is not None]
    total_credits = sum(g.course.credit for g in valid)
    weighted_gpa = sum((g.gpa or 0) * g.course.credit for g in valid)
    avg_gpa = round(weighted_gpa / total_credits, 2) if total_credits > 0 else 0
    avg_score = round(sum(g.score for g in valid) / len(valid), 2) if valid else 0

    return render_template('student/transcript.html', stu=stu, grades=grades,
                           avg_gpa=avg_gpa, avg_score=avg_score,
                           total_credits=total_credits, now=datetime.now())


@student_bp.route('/transcript/export')
@login_required
@role_required('student', 'super_admin', 'academic')
def transcript_export():
    """导出个人成绩单Excel"""
    stu = current_user.student
    if not stu:
        abort(404)
    grades = stu.grades.filter_by(exam_type='期末').all()

    headers = ['课程编号', '课程名称', '学分', '考核类型', '成绩', '等级', '绩点', '特殊标记', '班级排名']
    rows = []
    for g in grades:
        course_grades = Grade.query.filter_by(course_id=g.course_id, exam_type='期末').all()
        rankings = get_rankings(course_grades)
        rows.append([
            g.course.course_code, g.course.name, g.course.credit,
            g.course.assessment_type, g.score_display, g.grade_level,
            f'{g.gpa:.1f}' if g.gpa else '0.0', g.special_mark or '',
            f'{rankings.get(g.student_id, "-")}/{len(course_grades)}'
        ])

    valid = [g for g in grades if g.special_mark not in ('缺考', '作弊') and g.score is not None]
    total_credits = sum(g.course.credit for g in valid)
    weighted_gpa = sum((g.gpa or 0) * g.course.credit for g in valid)
    avg_gpa = round(weighted_gpa / total_credits, 2) if total_credits > 0 else 0
    avg_score = round(sum(g.score for g in valid) / len(valid), 2) if valid else 0

    summary_row = ['', '平均分', '', '', avg_score, '', f'平均GPA: {avg_gpa}', '', '']
    title = f'个人成绩单 - {stu.name}({stu.student_no})'
    wb = create_grade_export(title, headers, rows, summary_row)
    buf = export_to_bytes(wb)
    log_operation('export', '导出成绩单', f'学生 {stu.name}')
    return send_file(buf, as_attachment=True,
                     download_name=f'成绩单_{stu.name}_{stu.student_no}.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@student_bp.route('/ranking')
@login_required
@role_required('student', 'super_admin', 'academic')
def ranking():
    """班级排名"""
    stu = current_user.student
    if not stu or not stu.class_info:
        abort(404)
    # 获取同班所有学生的期末成绩
    classmates = stu.class_info.students.filter_by(status='正常').all()
    student_totals = []
    for s in classmates:
        grades = s.grades.filter_by(exam_type='期末').all()
        valid = [g for g in grades if g.special_mark not in ('缺考', '作弊') and g.score is not None]
        total_score = sum(g.score for g in valid)
        avg_score = round(total_score / len(valid), 2) if valid else 0
        total_credits = sum(g.course.credit for g in valid)
        weighted_gpa = sum((g.gpa or 0) * g.course.credit for g in valid)
        avg_gpa = round(weighted_gpa / total_credits, 2) if total_credits > 0 else 0
        student_totals.append({
            'student': s,
            'course_count': len(valid),
            'total_score': round(total_score, 2),
            'avg_score': avg_score,
            'avg_gpa': avg_gpa,
            'fail_count': sum(1 for g in grades if not g.is_pass),
        })
    # 按平均分排名
    student_totals.sort(key=lambda x: x['avg_score'], reverse=True)
    for rank, item in enumerate(student_totals, 1):
        item['rank'] = rank

    return render_template('student/ranking.html', stu=stu, rankings=student_totals)
