# pls don't die
print("Hello!")

import sqlite3
import os  # FIX 1: added missing import
from flask import Flask, render_template, request, redirect, session, flash, Response, url_for
import csv
from datetime import date, datetime, timedelta
import uuid
import io
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

app = Flask(__name__)
app.secret_key = "大家好" 

@app.route("/")
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == "s" and password == "s":
        session['logged_in'] = True
        return redirect('/dashboard') 
    else:
        flash("Invalid Username or Password.", "danger")
        return redirect('/')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect('/') 
    return render_template('executive_dashboard.html')

@app.route('/master-point-tracker')
def master_point_tracker():
    if not session.get('logged_in'):
        return redirect('/')

    leaderboard = []

    try:
        with open('members.csv', mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            conn = sqlite3.connect('science_club.db')
            cursor = conn.cursor()

            for row in reader:
                s_id = str(row.get('number', '')).strip()
                s_name = f"{row.get('first', '')} {row.get('last', '')}"

                cursor.execute("SELECT SUM(number_points) FROM POINTS WHERE student_number = ?", (s_id,))
                total = cursor.fetchone()[0]
                
                if total is None:
                    total = 0

                leaderboard.append({
                    'name': s_name,
                    'points': total
                })

            conn.close()

        leaderboard = sorted(leaderboard, key=lambda x: x['points'], reverse=True)

    except Exception as e:
        print(f"Error loading tracker: {e}")
        flash("Could not load point data.", "danger")

    return render_template('master_point_tracker.html', players=leaderboard)

@app.route('/modify-data', methods=['GET', 'POST'])
def modify_data():
    if not session.get('logged_in'):
        return redirect('/')

    all_members = []
    with open('members.csv', mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            s_id = str(row.get('number', '')).strip()
            name = f"{row.get('last')}, {row.get('first')}"
            
            conn = sqlite3.connect('science_club.db')
            cursor = conn.cursor()
            cursor.execute("SELECT sum(number_points) FROM POINTS WHERE student_number = ?", (s_id,))
            current_points = cursor.fetchone()[0] or 0
            conn.close()

            all_members.append({
                'id': s_id,
                'name': name,
                'display': f"{name} ({s_id}) - {current_points} pts",
                'points': current_points
            })

    if request.method == 'POST':
        selected_display = request.form.get('selected_member')
        action = request.form.get('action')
        amount = int(request.form.get('amount', 0))

        student_id = None
        for member in all_members:
            if member['display'] == selected_display:
                student_id = member['id']
                break
        
        if not student_id:
             flash("Please select a valid member from the list.", "danger")
             return redirect('/modify-data')
        if action == "subtract":
            amount = -abs(amount)
        
        try:
            conn = sqlite3.connect('science_club.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO POINTS (student_number, number_points) VALUES (?, ?)", (student_id, amount))
            conn.commit()
            conn.close()
            
            name_only = selected_display.split('(')[0].strip()
            action_word = "Added" if amount > 0 else "Deducted"
            flash(f"Successfully {action_word} {abs(amount)} points for {name_only}!", "success")
            return redirect('/dashboard')
            
        except Exception as e:
            flash(f"Database Error: {e}", "danger")

    return render_template('modify_data.html', members=all_members)


@app.route('/attendance')
def attendance():
    if not session.get('logged_in'):
        return redirect('/')

    attendance_history = []

    try:
        members_dict = {}
        with open('members.csv', mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                s_id = str(row.get('number', '')).strip()
                members_dict[s_id] = f"{row.get('first', '')} {row.get('last', '')}"

        conn = sqlite3.connect('science_club.db')
        cursor = conn.cursor()

        cursor.execute("SELECT student_number, attendance_date FROM ATTENDANCE ORDER BY attendance_date DESC")
        records = cursor.fetchall()

        for row in records:
            s_id = str(row[0])
            a_date = row[1]
            s_name = members_dict.get(s_id, "Unknown Member") 

            attendance_history.append({
                'date': a_date,
                'name': s_name,
                'id': s_id
            })

        conn.close()

    except Exception as e:
        print(f"Error loading attendance log: {e}")
        flash("Could not load attendance data.", "danger")

    return render_template('attendance.html', records=attendance_history)

@app.route('/quiz-creation', methods=['GET', 'POST'])
def quiz_creation():
    if not session.get('logged_in'):
        return redirect('/')

    if request.method == 'POST':
        questions = request.form.getlist('question_text[]')
        opt_a = request.form.getlist('opt_A[]')
        opt_b = request.form.getlist('opt_B[]')
        opt_c = request.form.getlist('opt_C[]')
        opt_d = request.form.getlist('opt_D[]')
        corrects = request.form.getlist('correct_ans[]')
        if not (len(questions) == len(opt_a) == len(opt_b) == len(opt_c) == len(opt_d) == len(corrects)):
            flash("Mismatched form data – each question must have all options and a correct answer.", "danger")
            return render_template('quiz_creation.html')

        quiz_ID = "QUIZ-" + str(uuid.uuid4())[:8]
        start_time = datetime.now().isoformat()

        try:
            conn = sqlite3.connect('science_club.db')
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS QUIZ_TIMERS (quizID TEXT, start_time TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS QUIZ_ATTEMPTS (student_id TEXT, quizID TEXT)")
            cursor.execute("INSERT INTO QUIZ_TIMERS (quizID, start_time) VALUES (?, ?)", (quiz_ID, start_time))

            for i in range(len(questions)):
                q_id = "Q-" + str(uuid.uuid4())[:8]
                cursor.execute("INSERT INTO QUESTIONS (questionID, question) VALUES (?, ?)", (q_id, questions[i]))

                options = [opt_a[i], opt_b[i], opt_c[i], opt_d[i]]
                correct_idx = int(corrects[i])  

                for j, opt_text in enumerate(options):
                    ans_id = "A-" + str(uuid.uuid4())[:8]
                    if j == correct_idx:
                        cursor.execute(
                            "INSERT INTO CORRECT_ANSWER (answerID, answer) VALUES (?, ?)",
                            (ans_id, opt_text)
                        )
                        cursor.execute(
                            "INSERT INTO QUIZ (quizID, questionID, answerID) VALUES (?, ?, ?)",
                            (quiz_ID, q_id, ans_id)
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO WRONG_ANSWERS (wrong_answerID, wrong_answer, questionID) VALUES (?, ?, ?)",
                            (ans_id, opt_text, q_id)
                        )

            conn.commit()
            conn.close()
            flash("Multi-question quiz published! Members have 1 hour to complete it.", "success")
            return redirect(url_for('quiz_creation'))

        except Exception as e:
            print("ERROR during quiz creation:", e)
            flash(f"Error saving quiz: {e}", "danger")
            return redirect(url_for('quiz_creation'))

    past_quizzes = []
    try:
        conn = sqlite3.connect('science_club.db')
        cursor = conn.cursor()
        cursor.execute("SELECT question FROM QUESTIONS")
        past_quizzes = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print("Error fetching past quizzes:", e)

    return render_template('quiz_creation.html', past_quizzes=past_quizzes)
    
@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if not session.get('logged_in'):
        return redirect('/')

    if request.method == 'POST':
        number = request.form.get('number', '').strip()
        first = request.form.get('first', '').strip()
        last = request.form.get('last', '').strip()
        if not number or not first or not last:
            flash("All fields are required.", "danger")
            return render_template('add_member.html')
        try:
            file_exists = os.path.isfile('members.csv')  # FIX 1: os is now imported
            with open('members.csv', mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['number', 'first', 'last'])
                writer.writerow([number, first, last])

            flash(f"Member {first} {last} added successfully.", "success")
            return redirect(url_for('attendance'))  # FIX 2: use function name, not template name

        except Exception as e:
            print(f"Error writing to members.csv: {e}")
            flash("Failed to add member. Please try again.", "danger")
            return render_template('add_member.html')
    return render_template('add_member.html')

@app.route('/export-data')
def export_data():
    if not session.get('logged_in'):
        return redirect('/')

    total_members = 0
    active_this_month = 0
    avg_attendance_pct = 0
    total_points = 0
    top_earners = []
    recent_quizzes = []
    overall_part_rate = 0

    conn = None
    try:
        conn = sqlite3.connect('science_club.db')
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM MEMBER")
        row = cursor.fetchone()
        total_members = row[0] if row else 0

        cursor.execute("""
            SELECT COUNT(DISTINCT student_number)
            FROM ATTENDANCE
            WHERE strftime('%Y-%m', attendance_date) = strftime('%Y-%m', 'now')
        """)
        row = cursor.fetchone()
        active_this_month = row[0] if row else 0

        cursor.execute("SELECT COUNT(*) FROM ATTENDANCE GROUP BY attendance_date")
        daily_counts = [r[0] for r in cursor.fetchall()]
        if daily_counts and total_members > 0:
            avg_raw = sum(daily_counts) / len(daily_counts)
            avg_attendance_pct = int((avg_raw / total_members) * 100)

        cursor.execute("""
            SELECT SUM(number_points)
            FROM POINTS
            WHERE award_date >= date('now', 'weekday 0', '-7 days')
        """)
        row = cursor.fetchone()
        total_points = row[0] if row and row[0] else 0

        cursor.execute("""
            SELECT m.Firstname, m.Lastname, COALESCE(SUM(p.number_points), 0) as total
            FROM MEMBER m
            LEFT JOIN POINTS p ON m.Student_number = p.student_number
                AND p.award_date >= date('now', 'weekday 0', '-7 days')
            GROUP BY m.Student_number
            ORDER BY total DESC
            LIMIT 5
        """)
        top_earners = cursor.fetchall()

        cursor.execute("""
            SELECT qst.question, q.quizID
            FROM QUIZ q
            JOIN QUESTIONS qst ON q.questionID = qst.questionID
            ORDER BY q.quizID DESC
            LIMIT 3
        """)
        recent_quizzes_raw = cursor.fetchall()

        # FIX 3: use consistent variable name quiz_ID (was quiz_aID in loop but quiz_ID in query)
        for question_text, quiz_ID in recent_quizzes_raw:
            cursor.execute("""
                SELECT COUNT(DISTINCT student_id)
                FROM QUIZ_ATTEMPTS
                WHERE quizID = ?
            """, (quiz_ID,))
            attempts = cursor.fetchone()[0]
            part_rate = int((attempts / total_members) * 100) if total_members > 0 else 0
            short_title = (question_text[:40] + '...') if len(question_text) > 40 else question_text
            recent_quizzes.append({
                'title': short_title,
                'rate': part_rate
            })

        cursor.execute("SELECT COUNT(DISTINCT student_id) FROM QUIZ_ATTEMPTS")
        active_takers = cursor.fetchone()[0]
        overall_part_rate = int((active_takers / total_members) * 100) if total_members > 0 else 0

    except sqlite3.Error as e:
        print(f"Export error: {e}")
    finally:
        if conn:
            conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    story = []  

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']

    story.append(Paragraph("Science Club Weekly Report", title_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    story.append(Spacer(1, 0.2 * inch))

    data_summary = [
        ["Metric", "Value"],
        ["Total Members", total_members],
        ["Active This Month", active_this_month],
        ["Avg Attendance %", f"{avg_attendance_pct}%"],
        ["Total Points Awarded (This Week)", total_points],
        ["Overall Quiz Participation", f"{overall_part_rate}%"]
    ]

    table_summary = Table(data_summary, colWidths=[2.5*inch, 1.5*inch])
    table_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table_summary)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Top 5 Point Earners (This Week)", heading_style))
    data_top = [["Rank", "Name", "Points"]]
    for idx, (first, last, pts) in enumerate(top_earners, 1):
        data_top.append([idx, f"{first} {last}", pts])

    if len(top_earners) == 0:
        data_top.append(["", "No data available", ""])

    table_top = Table(data_top, colWidths=[0.8*inch, 3.0*inch, 1.2*inch])
    table_top.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table_top)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Recent Quiz Participation", heading_style))
    data_quiz = [["Quiz Title", "Participation Rate"]]
    for q in recent_quizzes:
        data_quiz.append([q['title'], f"{q['rate']}%"])
    if not recent_quizzes:
        data_quiz.append(["No quizzes published yet", ""])

    table_quiz = Table(data_quiz, colWidths=[3.5*inch, 1.5*inch])
    table_quiz.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table_quiz)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment;filename=club_report.pdf'}
    )

@app.route('/report-page')
def report_page():
    if not session.get('logged_in'):
        return redirect('/')

    total_members = 0
    active_this_month = 0
    avg_attendance_pct = 0
    total_points = 0
    top_earners = []
    recent_quizzes = []
    overall_part_rate = 0

    conn = None
    try:
        conn = sqlite3.connect('science_club.db')
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM MEMBER")
            row = cursor.fetchone()
            total_members = row[0] if row else 0

            cursor.execute("""
                SELECT COUNT(DISTINCT student_number)
                FROM ATTENDANCE
                WHERE strftime('%Y-%m', attendance_date) = strftime('%Y-%m', 'now')
            """)
            row = cursor.fetchone()
            active_this_month = row[0] if row else 0
        except sqlite3.OperationalError as e:
            print(f"Table missing (MEMBER/ATTENDANCE): {e}")

        try:
            cursor.execute("SELECT COUNT(*) FROM ATTENDANCE GROUP BY attendance_date")
            daily_counts = [r[0] for r in cursor.fetchall()]
            if daily_counts and total_members > 0:
                avg_raw = sum(daily_counts) / len(daily_counts)
                avg_attendance_pct = int((avg_raw / total_members) * 100)
        except sqlite3.OperationalError as e:
            print(f"Attendance table issue: {e}")

        try:
            cursor.execute("""
                SELECT SUM(number_points)
                FROM POINTS
                WHERE award_date >= date('now', 'weekday 0', '-7 days')
            """)
            row = cursor.fetchone()
            total_points = row[0] if row and row[0] else 0
        except sqlite3.OperationalError as e:
            print(f"Points query failed (check award_date column): {e}")
            total_points = 0

        try:
            cursor.execute("""
                SELECT m.Firstname, m.Lastname, COALESCE(SUM(p.number_points), 0) as total
                FROM MEMBER m
                LEFT JOIN POINTS p ON m.Student_number = p.student_number
                    AND p.award_date >= date('now', 'weekday 0', '-7 days')
                GROUP BY m.Student_number
                ORDER BY total DESC
                LIMIT 5
            """)
            top_earners = cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"Top earners query failed: {e}")
            top_earners = []

        try:
            cursor.execute("""
                SELECT qst.question, q.quizID
                FROM QUIZ q
                JOIN QUESTIONS qst ON q.questionID = qst.questionID
                ORDER BY q.quizID DESC
                LIMIT 3
            """)
            recent_quizzes_raw = cursor.fetchall()

            for question_text, quiz_ID in recent_quizzes_raw:  # FIX 3: consistent variable name
                cursor.execute("""
                    SELECT COUNT(DISTINCT student_id)
                    FROM QUIZ_ATTEMPTS
                    WHERE quizID = ?
                """, (quiz_ID,))
                attempts = cursor.fetchone()[0]
                part_rate = int((attempts / total_members) * 100) if total_members > 0 else 0

                if part_rate >= 80:
                    bar_class = "excellent"
                elif part_rate >= 50:
                    bar_class = ""
                else:
                    bar_class = "warning"

                short_title = (question_text[:40] + '...') if len(question_text) > 40 else question_text

                recent_quizzes.append({
                    'title': short_title,
                    'rate': part_rate,
                    'bar_class': bar_class
                })

            cursor.execute("SELECT COUNT(DISTINCT student_id) FROM QUIZ_ATTEMPTS")
            active_takers = cursor.fetchone()[0]
            overall_part_rate = int((active_takers / total_members) * 100) if total_members > 0 else 0

        except sqlite3.OperationalError as e:
            print(f"Quiz tables missing (maybe QUIZ_ATTEMPTS not created): {e}")

    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
    finally:
        if conn:
            conn.close()

    return render_template('report_page.html',
                           total_members=total_members,
                           active_this_month=active_this_month,
                           avg_attendance_pct=avg_attendance_pct,
                           total_points=total_points,
                           top_earners=top_earners,
                           recent_quizzes=recent_quizzes,
                           overall_part_rate=overall_part_rate)

# --- MEMBER SECTION ---
@app.route('/member-login', methods=['POST'])
def member_login():
    session.clear() 
    
    user_id = request.form.get('student_num', '').strip()
    user_last = request.form.get('last_name', '').strip().lower()

    try:
        with open('members.csv', mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                csv_id = str(row.get('number', '')).strip()
                csv_last = str(row.get('last', '')).strip().lower()

                if csv_id == user_id and csv_last == user_last:
                    session['logged_in'] = True
                    session['first_name'] = str(row.get('first', 'Member')).strip()
                    session['student_id'] = csv_id

                    try:
                        conn = sqlite3.connect('science_club.db')
                        cursor = conn.cursor()
                        cursor.execute("SELECT SUM(number_points) FROM POINTS WHERE student_number = ?", (csv_id,))
                        total_points = cursor.fetchone()[0]
                        if total_points is None:
                            total_points = 0
                        session['points'] = total_points
                        
                    except Exception as db_error:
                        print(f"Database Error: {db_error}")
                        session['points'] = 0 
                    finally:
                        conn.close()
                    
                    return redirect('/member-dashboard')
                    
    except Exception as e:
        print(f"Error: {e}")
        flash("System Error: Could not read members.csv", "danger")
        return redirect('/')

    flash("Invalid ID or Last Name.", "danger")
    return redirect('/')
    
@app.route('/member-dashboard')
def member_dashboard():
    if not session.get('logged_in'):
        return redirect('/')
    student_id = session.get('student_id')
    try:
        conn = sqlite3.connect('science_club.db')
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(number_points) FROM POINTS WHERE student_number = ?", (student_id,))
        total = cursor.fetchone()[0] or 0
        session['points'] = total 
        conn.close()
    except:
        session['points'] = 0

    return render_template('member_dashboard.html')

@app.route('/attendance-form', methods=['GET', 'POST'])
def attendance_form():
    if not session.get('logged_in'):
        return redirect('/')

    if request.method == 'POST':
        coming_today = request.form.get('coming_today')
        student_id = session.get('student_id')
        
        today_date = date.today().strftime("%Y-%m-%d")

        try:
            if coming_today == 'yes':
                conn = sqlite3.connect('science_club.db')
                cursor = conn.cursor()
                new_attendance_id = "ATT-" + str(uuid.uuid4())[:8]
                cursor.execute('''
                    INSERT INTO ATTENDANCE (attendanceID, student_number, attendance_date)
                    VALUES (?, ?, ?)
                ''', (new_attendance_id, student_id, today_date))
                
                conn.commit()
                conn.close()
                
                flash("Awesome! We'll see you at the club today.", "success")
                
            else:
                flash("Aww, we'll miss you! Thanks for letting us know.", "info")

        except Exception as e:
            print(f"Database Error: {e}")
            flash("Oops! Something went wrong saving your attendance.", "danger")
            
        return redirect('/member-dashboard')
    return render_template('attendance_form.html')

@app.route('/quiz-taking', methods=['GET', 'POST'])
def take_quiz():
    if not session.get('logged_in'):
        return redirect('/')

    student_id = session.get('student_id')
    
    conn = sqlite3.connect('science_club.db')
    cursor = conn.cursor()

    cursor.execute("SELECT quizID, start_time FROM QUIZ_TIMERS ORDER BY rowid DESC LIMIT 1")
    latest_quiz = cursor.fetchone()

    if not latest_quiz:
        conn.close()
        return render_template('quiz_taking.html', error="No quiz currently available.")

    quiz_ID, start_str = latest_quiz
    start_time = datetime.fromisoformat(start_str)

    if datetime.now() > start_time + timedelta(hours=1):
        conn.close()
        return render_template('quiz_taking.html', error="The time window for this quiz has expired!")

    cursor.execute("SELECT * FROM QUIZ_ATTEMPTS WHERE student_id=? AND quizID=?", (student_id, quiz_ID))
    if cursor.fetchone():
        conn.close()
        return render_template('quiz_taking.html', error="You have already completed this week's quiz!")

    # FIX 5: actually handle POST — grade the quiz and award points
    if request.method == 'POST':
        cursor.execute("SELECT questionID FROM QUIZ WHERE quizID=?", (quiz_ID,))
        question_ids = [row[0] for row in cursor.fetchall()]

        score = 0
        for q_id in question_ids:
            submitted = request.form.get(f'answer_{q_id}')
            cursor.execute(
                "SELECT answer FROM CORRECT_ANSWER WHERE answerID = "
                "(SELECT answerID FROM QUIZ WHERE questionID=? AND quizID=?)",
                (q_id, quiz_ID)
            )
            correct_row = cursor.fetchone()
            if correct_row and submitted == correct_row[0]:
                score += 1

        attempt_id = "ATT-" + str(uuid.uuid4())[:8]
        cursor.execute(
            "INSERT INTO QUIZ_ATTEMPTS (student_id, quizID) VALUES (?, ?)",
            (student_id, quiz_ID)
        )

        if score > 0:
            cursor.execute(
                "INSERT INTO POINTS (student_number, number_points) VALUES (?, ?)",
                (student_id, score)
            )

        conn.commit()
        conn.close()

        flash(f"Quiz submitted! You got {score}/{len(question_ids)} correct and earned {score} points.", "success")
        return redirect('/member-dashboard')

    cursor.execute("SELECT questionID FROM QUIZ WHERE quizID=?", (quiz_ID,))
    question_ids = [row[0] for row in cursor.fetchall()]

    quiz_data = []
    for q_id in question_ids:
        cursor.execute("SELECT question FROM QUESTIONS WHERE questionID=?", (q_id,))
        q_text = cursor.fetchone()[0]
        cursor.execute("SELECT answer FROM CORRECT_ANSWER WHERE answerID IN (SELECT answerID FROM QUIZ WHERE questionID=?)", (q_id,))
        correct_ans = cursor.fetchone()[0]

        cursor.execute("SELECT wrong_answer FROM WRONG_ANSWERS WHERE questionID=? ORDER BY RANDOM() LIMIT 3", (q_id,))
        wrong_options = [row[0] for row in cursor.fetchall()]
        options = wrong_options + [correct_ans]
        random.shuffle(options)

        quiz_data.append({'q_id': q_id, 'text': q_text, 'options': options})

    conn.close()
    return render_template('quiz_taking.html', quiz_data=quiz_data, quiz_id=quiz_ID)


@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    if not session.get('logged_in'):
        return redirect('/')
    student_number = session.get('student_id')
    if not student_number:
        student_number = request.form.get('student_number')
        
    quiz_id = request.form.get('quiz_id')
    if not student_number or not quiz_id:
        return "Error: Missing student number or quiz ID!", 400

    try:
        conn = sqlite3.connect('science_club.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO QUIZ_ATTEMPTS (student_id, quizID) 
            VALUES (?, ?)
        """, (student_number, quiz_id))
        conn.commit()
        
    except Exception as e:
        print("Quiz Submission Error:", e)
    finally:
        conn.close()
    return redirect('/member-dashboard')


@app.route('/logout')
def logout():
    session.clear() 
    flash("You have been logged out.", "info")
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)