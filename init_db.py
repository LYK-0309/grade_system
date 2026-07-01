"""
数据库初始化脚本 - 创建表 + 导入Excel数据 + 创建默认账号
用法: python init_db.py
"""
import os
import sys
import pandas as pd
from datetime import datetime

# 确保能导入app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, User, ClassInfo, Student, Teacher, Course, Grade, SystemSetting

EXCEL_PATH = r'C:\Users\刘聿康\Desktop\23本计算机科学与技术6班_统计一键导出.xlsx'


def init_database():
    app = create_app()
    with app.app_context():
        print('正在创建数据库表...')
        db.create_all()

        # 1. 创建超级管理员
        if not User.query.filter_by(username='LYK').first():
            admin = User(username='LYK', name='刘聿康', role='super_admin')
            admin.set_password('lhs623')
            db.session.add(admin)
            print('  [OK] 超级管理员: LYK / lhs623')

        # 2. 创建教师
        teacher = Teacher.query.filter_by(teacher_no='T001').first()
        if not teacher:
            teacher = Teacher(teacher_no='T001', name='杨许亮', department='人工智能学院')
            db.session.add(teacher)
            db.session.flush()
            # 创建教师账号
            if not User.query.filter_by(username='yangxuliang').first():
                t_user = User(username='yangxuliang', name='杨许亮', role='teacher')
                t_user.set_password('123456')
                t_user.teacher = teacher
                db.session.add(t_user)
            print('  [OK] 教师账号: yangxuliang / 123456')

        # 创建教务管理员
        if not User.query.filter_by(username='jiaowu').first():
            jw = User(username='jiaowu', name='教务管理员', role='academic')
            jw.set_password('123456')
            db.session.add(jw)
            print('  [OK] 教务账号: jiaowu / 123456')

        # 3. 创建班级
        cls = ClassInfo.query.filter_by(name='23本计算机科学与技术6班').first()
        if not cls:
            cls = ClassInfo(
                name='23本计算机科学与技术6班',
                grade='23本',
                major='计算机科学与技术',
                duration='4年'
            )
            db.session.add(cls)
            db.session.flush()
            print('  [OK] 班级: 23本计算机科学与技术6班')

        # 4. 创建课程
        course = Course.query.filter_by(course_code='CS101').first()
        if not course:
            course = Course(
                course_code='CS101',
                name='计算机前沿技术',
                credit=2.0,
                hours=32,
                assessment_type='考查',
                teacher_id=teacher.id,
                class_id=cls.id,
                semester='2025-2026-2'
            )
            db.session.add(course)
            db.session.flush()
            print('  [OK] 课程: 计算机前沿技术 (CS101)')

        # 5. 导入Excel数据
        if os.path.exists(EXCEL_PATH):
            print(f'\n正在导入Excel数据: {EXCEL_PATH}')
            df = pd.read_excel(EXCEL_PATH, sheet_name='综合成绩', header=2)
            # 重命名列
            df.columns = ['序号', '学生姓名', '学号', '院系', '专业', '班级',
                          '讨论', '作业', '签到', '课程积分', 'PBL', '综合成绩']
            imported = 0
            for _, row in df.iterrows():
                if pd.isna(row['学号']) or pd.isna(row['学生姓名']):
                    continue
                student_no = str(row['学号']).strip().split('.')[0]
                name = str(row['学生姓名']).strip()

                # 创建/更新学生
                stu = Student.query.filter_by(student_no=student_no).first()
                if not stu:
                    stu = Student(
                        student_no=student_no,
                        name=name,
                        class_id=cls.id,
                        college=str(row['院系']) if not pd.isna(row['院系']) else '人工智能学院',
                        major=str(row['专业']) if not pd.isna(row['专业']) else '计算机科学与技术',
                        status='正常'
                    )
                    db.session.add(stu)
                    db.session.flush()
                else:
                    stu.name = name

                # 创建学生账号
                if not User.query.filter_by(username=student_no).first():
                    s_user = User(username=student_no, name=name, role='student')
                    s_user.set_password(student_no)
                    s_user.student = stu
                    db.session.add(s_user)

                # 创建成绩
                def safe_float(val):
                    if pd.isna(val):
                        return None
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None

                score = safe_float(row['综合成绩'])
                discuss = safe_float(row['讨论'])
                homework = safe_float(row['作业'])
                attendance = safe_float(row['签到'])
                points = safe_float(row['课程积分'])
                pbl = safe_float(row['PBL'])

                grade = Grade.query.filter_by(
                    student_id=stu.id, course_id=course.id, exam_type='期末'
                ).first()
                if not grade:
                    grade = Grade(
                        student_id=stu.id,
                        course_id=course.id,
                        exam_type='期末',
                        created_by=1
                    )
                    db.session.add(grade)

                grade.score = score
                grade.score_discuss = discuss
                grade.score_homework = homework
                grade.score_attendance = attendance
                grade.score_points = points
                grade.score_pbl = pbl
                grade.gpa = Grade.calc_gpa(score)
                imported += 1

            db.session.commit()
            print(f'  [OK] 导入 {imported} 条学生成绩')
        else:
            print(f'  [SKIP] Excel文件不存在: {EXCEL_PATH}')

        # 6. 系统默认设置
        defaults = {
            'max_score': '100',
            'pass_score': '60',
            'excellent_score': '90',
            'current_semester': '2025-2026-2',
            'gpa_rule': '4.0制',
        }
        for k, v in defaults.items():
            if not SystemSetting.query.filter_by(key=k).first():
                db.session.add(SystemSetting(key=k, value=v, description=k))
        db.session.commit()
        print('  [OK] 系统设置已初始化')

        print('\n========================================')
        print('  数据库初始化完成!')
        print('  超管: LYK / lhs623')
        print('  教师: yangxuliang / 123456')
        print('  教务: jiaowu / 123456')
        print('  学生: 学号 / 学号 (如 423240601)')
        print('========================================')
        print('\n启动: python run.py')
        print('访问: http://127.0.0.1:5000')


if __name__ == '__main__':
    init_database()
