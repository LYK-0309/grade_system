"""导入 23本计算机科学与技术6班 计算机前沿技术 成绩数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from app import create_app
from app.models import db, User, Student, Teacher, Course, ClassInfo, Grade

app = create_app()

EXCEL_PATH = r'C:/Users/刘聿康/Desktop/23本计算机科学与技术6班_统计一键导出.xlsx'

with app.app_context():
    # ── 读取Excel ──
    df = pd.read_excel(EXCEL_PATH, header=None)
    # row0=标题 row1=课程/班级/教师/时间（合并单元格，同在列0） row2=表头
    import re
    info_str = str(df.iloc[1, 0])
    course_name = re.search(r'课程[：:]\s*(.+?)(?:\s{2,}|$)', info_str).group(1).strip()
    class_name = re.search(r'班级[：:]\s*(.+?)(?:\s{2,}|$)', info_str).group(1).strip()
    teacher_name = re.search(r'任课教师[：:]\s*(.+?)(?:\s{2,}|$)', info_str).group(1).strip()
    export_time = re.search(r'导出时间[：:]\s*(.+?)$', info_str).group(1).strip()

    print(f'课程: {course_name}')
    print(f'班级: {class_name}')
    print(f'教师: {teacher_name}')
    print(f'导出时间: {export_time}')
    print()

    # ── 1. 创建班级 ──
    cls = ClassInfo.query.filter_by(name=class_name).first()
    if not cls:
        cls = ClassInfo(name=class_name, grade='23本', major='计算机科学与技术', duration='4年')
        db.session.add(cls)
        db.session.flush()
        print(f'[创建] 班级: {class_name}')
    else:
        print(f'[已存在] 班级: {class_name}')

    # ── 2. 创建教师账号 ──
    teacher_no = 'T' + teacher_name  # 简单工号规则
    teacher_user = User.query.filter_by(username=teacher_no).first()
    if not teacher_user:
        teacher_user = User(username=teacher_no, name=teacher_name, role='teacher')
        teacher_user.set_password('123456')
        db.session.add(teacher_user)
        db.session.flush()
        print(f'[创建] 教师账号: {teacher_no}')
    else:
        print(f'[已存在] 教师账号: {teacher_no}')

    t = Teacher.query.filter_by(teacher_no=teacher_no).first()
    if not t:
        t = Teacher(teacher_no=teacher_no, name=teacher_name,
                    department='人工智能学院', user_id=teacher_user.id)
        db.session.add(t)
        db.session.flush()
        print(f'[创建] 教师: {teacher_name}')
    else:
        print(f'[已存在] 教师: {teacher_name}')

    # ── 3. 创建课程 ──
    course_code = 'JSQYJS'  # 计算机前沿技术
    course = Course.query.filter_by(course_code=course_code).first()
    if not course:
        course = Course(course_code=course_code, name=course_name,
                        credit=2.0, hours=32, assessment_type='考查',
                        teacher_id=t.id, class_id=cls.id, semester='2025-2026-2')
        db.session.add(course)
        db.session.flush()
        print(f'[创建] 课程: {course_name} ({course_code})')
    else:
        print(f'[已存在] 课程: {course_name} ({course_code})')

    db.session.commit()

    # ── 4. 导入学生和成绩 ──
    data_start = 3  # 数据从第4行(row index 3)开始
    created_students = 0
    created_grades = 0
    skipped_grades = 0

    for i in range(data_start, len(df)):
        row = df.iloc[i]
        seq = int(row[0])
        name = str(row[1]).strip()
        student_no = str(int(row[2])).strip()
        college = str(row[3]).strip() if pd.notna(row[3]) else '人工智能学院'
        major = str(row[4]).strip() if pd.notna(row[4]) else '计算机科学与技术'

        score_discuss = float(row[6]) if pd.notna(row[6]) else 0
        score_homework = float(row[7]) if pd.notna(row[7]) else 0
        score_attendance = float(row[8]) if pd.notna(row[8]) else 0
        score_points = float(row[9]) if pd.notna(row[9]) else 0
        score_pbl = float(row[10]) if pd.notna(row[10]) else 0
        score_total = float(row[11]) if pd.notna(row[11]) else 0

        # 创建学生账号
        user = User.query.filter_by(username=student_no).first()
        if not user:
            user = User(username=student_no, name=name, role='student')
            user.set_password(student_no)  # 默认密码为学号
            db.session.add(user)
            db.session.flush()

        # 创建学生记录
        stu = Student.query.filter_by(student_no=student_no).first()
        if not stu:
            stu = Student(student_no=student_no, name=name,
                         class_id=cls.id, college=college, major=major,
                         user_id=user.id, status='正常')
            db.session.add(stu)
            db.session.flush()
            created_students += 1

        # 创建成绩记录
        existing_grade = Grade.query.filter_by(
            student_id=stu.id, course_id=course.id, exam_type='期末'
        ).first()
        if existing_grade:
            skipped_grades += 1
            continue

        gpa = Grade.calc_gpa(score_total)
        grade = Grade(
            student_id=stu.id, course_id=course.id,
            score=score_total,
            score_discuss=score_discuss,
            score_homework=score_homework,
            score_attendance=score_attendance,
            score_points=score_points,
            score_pbl=score_pbl,
            gpa=gpa, exam_type='期末'
        )
        db.session.add(grade)
        created_grades += 1

    db.session.commit()

    print()
    print('=' * 50)
    print(f'导入完成！')
    print(f'  新增学生: {created_students}')
    print(f'  新增成绩: {created_grades}')
    if skipped_grades:
        print(f'  跳过(已有成绩): {skipped_grades}')
    print('=' * 50)
