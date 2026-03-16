# pls don't die
print("Hello!")

import sqlite3  # lets us interact with SQLite databases
import os  # gives access to operating system functions like file paths
from flask import Flask, render_template, request, redirect, session, flash, Response, url_for  # imports core Flask tools for building the web app
import csv  # lets us read and write CSV files
from datetime import date, datetime, timedelta  # imports date/time tools for handling timestamps and durations
import uuid  # generates unique IDs for quizzes, questions, etc.
import io  # lets us work with in-memory byte streams (used for PDF generation)
import random  # lets us shuffle quiz answer options
from reportlab.pdfgen import canvas  # low-level PDF drawing tool from ReportLab
from reportlab.lib.pagesizes import letter, landscape  # standard page size constants for PDFs
from reportlab.lib import colors  # provide colors for PDF styling
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer  # high-level PDF layout components
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # pre-built text styles for PDFs
from reportlab.lib.units import inch  # uses inches as a unit of measurement in PDFs
import bcrypt  # used to securely hash and check passwords


app = Flask(__name__)  # creates the Flask web application instance
app.secret_key = "大家好"  # secret key used to sign and secure session cookies

@app.route("/")  # maps the root URL "/" to the home function
def home():
    return render_template('login.html')  # serves the login page when someone visits the site

DATABASE = 'science_club.db'  # stores the filename of the SQLite database

def get_db():
    conn = sqlite3.connect(DATABASE)  # opens a connection to the SQLite database file
    return conn  # returns the connection so it can be used by other functions

@app.route('/login', methods=['POST']) 
def login():
    #grabs what the user inputted in the html file 
    username = request.form.get('username')  # read username from frontend
    password = request.form.get('password')  # read password from frontend  
    #opens EXECUTIVE table 
    conn = get_db() # connects to database
    cursor = conn.cursor()  # create cursor to run SQL commands
    cursor.execute("SELECT Password FROM EXECUTIVE WHERE Username = ?", (username,))  # looks up the hashed password for the given username
    user = cursor.fetchone()  # fetches the first matching row, or None if not found
    conn.close() # closes database 
    #checks if username and password is correct 
    if user and bcrypt.checkpw(password.encode('utf-8'), user[0].encode('utf-8')):  # checks if password is equal to the hashed one
        session['logged_in'] = True  # allows them to login
        return redirect('/dashboard')  # takes them to the exec homepage 
    else:
        flash("Invalid Username or Password.", "danger")  # shows an error message on the login page
        return redirect('/')
        # reloads current page 

@app.route('/dashboard')  # maps /dashboard URL to this function
def dashboard():
    if not session.get('logged_in'):
        return redirect('/') 
    return render_template('executive_dashboard.html')  # loads the executive dashboard page

def merge_sort(arr):  # recursive merge sort function that sorts members by points (descending)
    if len(arr) <= 1:  # base case: a list of 0 or 1 items is already sorted
        return arr
    mid = len(arr) // 2  # finds the midpoint to split the list
    left = merge_sort(arr[:mid])  # recursively sorts the left half
    right = merge_sort(arr[mid:])  # recursively sorts the right half
    return merge(left, right)  # merges the two sorted halves together

def merge(left, right):  # combines two sorted lists into one sorted list
    result = []  # empty list to hold the merged output
    i = j = 0  # index pointers for the left and right lists
    while i < len(left) and j < len(right):  # loops until one list runs out
        if left[i]['points'] >= right[j]['points']:  # compares points values (higher points go first)
            result.append(left[i])  # adds the left item if it has more or equal points
            i += 1  # moves the left pointer forward
        else:
            result.append(right[j])  # adds the right item if it has more points
            j += 1  # moves the right pointer forward
    result.extend(left[i:])  # appends any remaining items from the left list
    result.extend(right[j:])  # appends any remaining items from the right list
    return result  # returns the fully merged and sorted list

@app.route('/master-point-tracker') 
def master_point_tracker():
    if not session.get('logged_in'):
        # makes sures the user is logged in 
        return redirect('/') 
    leaderboard = [] # creates an empty list 
    try:
        conn = get_db()
        cursor = conn.cursor() # opens connection with database
        # get all members from the database
        cursor.execute("SELECT Student_number, Firstname, Lastname FROM MEMBER") # gets the data
        members = cursor.fetchall() # fetchall returns a list with the data
        for member in members: 
            s_id = str(member[0]).strip()  # converts student number to string and removes whitespace
            s_name = f"{member[1]} {member[2]}" # name becomes first name + last name 
            cursor.execute("SELECT SUM(number_points) FROM POINTS WHERE student_number = ?", (s_id,))
            total = cursor.fetchone()[0]
            if total is None:
                total = 0  # if they dont have points it is 0 --> doesnt break code 
            leaderboard.append({ # adds member as a dict
                'name': s_name,
                'points': total
            })
        conn.close() # closes database 
        leaderboard = merge_sort(leaderboard)  # merge sorts it 
    except Exception as e:
        print(f"Error loading tracker: {e}")
        flash("Could not load point data.", "danger") # handles errors 
    return render_template('master_point_tracker.html', players=leaderboard) # opens html file 


@app.route('/modify-data', methods=['GET', 'POST'])
def modify_data():
    if not session.get('logged_in'):
        return redirect('/')
    all_members = []  #  store all member data as a list of dicts
    try:
        # open one connection for the entire route instead of once per member
        conn = get_db()
        cursor = conn.cursor()
        # gets all members directly from the MEMBER table
        cursor.execute("SELECT Student_number, Firstname, Lastname FROM MEMBER")
        members = cursor.fetchall()
        for member in members:
            s_id = str(member[0]).strip()  # converts student number to string and trims whitespace
            name = f"{member[2]}, {member[1]}" # formats as Lastname, Firstname
            # gets total points for this member from the POINTS table
            cursor.execute("SELECT SUM(number_points) FROM POINTS WHERE student_number = ?", (s_id,))
            current_points = cursor.fetchone()[0] or 0 # defaults to 0 if no points
            all_members.append({
                'id': s_id,
                'name': name,
                'display': f"{name} ({s_id}) - {current_points} pts",  # formats the dropdown label shown in the UI
                'points': current_points
            })
        conn.close() # closes connection after building the full member list
    except Exception as e:
        flash(f"Could not load members: {e}", "danger")
    if request.method == 'POST':  # only run when the form has been submitted
        selected_display = request.form.get('selected_member')  # get selected member's display string from the dropdown
        action = request.form.get('action')  # finds action is "add" or "subtract"
        amount = int(request.form.get('amount', 0))  # finds the point amount, defaulting to 0 if missing
        # finds the matching member from the list using their display string
        student_id = None
        for member in all_members:
            if member['display'] == selected_display:
                student_id = member['id']  # stores the student ID once a match is found
                break
        if not student_id:
             flash("Please select a valid member from the list.", "danger")
             return redirect('/modify-data')
        if action == "subtract":
            amount = -abs(amount) # makes the amount negative if subtracting
        try:
            conn = get_db()
            cursor = conn.cursor()
            # inserts a new points record for the selected member
            cursor.execute("INSERT INTO POINTS (student_number, number_points, award_date) VALUES (?, ?, ?)",
            (student_id, amount, date.today())
            )
            conn.commit()
            conn.close()
            name_only = selected_display.split('(')[0].strip()  # extract the name part from the display string
            action_word = "Added" if amount > 0 else "Deducted"  # picks either added or deducted 
            flash(f"Successfully {action_word} {abs(amount)} points for {name_only}!", "success")
            return redirect('/dashboard')        
        except Exception as e:
            flash(f"Database Error: {e}", "danger")
    return render_template('modify_data.html', members=all_members)


@app.route('/attendance') 
def attendance():
    if not session.get('logged_in'):
        return redirect('/')
    attendance_history = []  # stores records as a dict 
    try:
        conn = get_db()
        cursor = conn.cursor()
        # build a lookup dict of student_number -> full name directly from MEMBER table
        cursor.execute("SELECT Student_number, Firstname, Lastname FROM MEMBER")
        members_dict = {
            str(row[0]).strip(): f"{row[1]} {row[2]}"  # maps each student number to their full name
            for row in cursor.fetchall()
        }
        # attendance records are ordered by most recent
        cursor.execute("SELECT student_number, attendance_date FROM ATTENDANCE ORDER BY attendance_date DESC")
        records = cursor.fetchall()
        for row in records:
            s_id = str(row[0])  # converts student number to string
            a_date = row[1]  # stores the attendance date
            s_name = members_dict.get(s_id, "Unknown Member") # fallback if member not found
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


@app.route('/quiz-creation', methods=['GET', 'POST'])  # handles both loading the page and submitting the quiz form
def quiz_creation():
    if not session.get('logged_in'): # checks if user is logged in
        return redirect('/')
    if request.method == 'POST': # runs when the form is submitted
        # grabs all questions and their options as lists from the form
        questions = request.form.getlist('question_text[]')
        opt_a = request.form.getlist('opt_A[]')
        opt_b = request.form.getlist('opt_B[]')
        opt_c = request.form.getlist('opt_C[]')
        opt_d = request.form.getlist('opt_D[]')
        corrects = request.form.getlist('correct_ans[]') # index of the correct answer for each question
        # validates that every question has all 4 options and a correct answer
        if not (len(questions) == len(opt_a) == len(opt_b) == len(opt_c) == len(opt_d) == len(corrects)):
            flash("Mismatched form data - each question must have all options and a correct answer.", "danger")
            return render_template('quiz_creation.html')
        # generates a unique quiz
        quiz_ID = "QUIZ-" + str(uuid.uuid4())[:8]
        # records the current time to start the 1 hour countdown
        start_time = datetime.now().isoformat()
        try:
            conn = get_db() 
            cursor = conn.cursor()
            # saves the quiz ID and start time to start the timer
            cursor.execute("INSERT INTO QUIZ_TIMERS (quizID, start_time) VALUES (?, ?)", (quiz_ID, start_time))
            # loops through each question in the form
            for i in range(len(questions)):
                # creates a unique question ID 
                q_id = "Q-" + str(uuid.uuid4())[:8]
                # saves the question text to the QUESTIONS table
                cursor.execute("INSERT INTO QUESTIONS (questionID, question) VALUES (?, ?)", (q_id, questions[i]))
                # all 4 options into a list
                options = [opt_a[i], opt_b[i], opt_c[i], opt_d[i]]
                # gets the index of the correct answer (0-3)
                correct_idx = int(corrects[i])
                # loops through each option for this question
                for j, opt_text in enumerate(options):
                    # generates a unique answer
                    ans_id = "A-" + str(uuid.uuid4())[:8]
                    if j == correct_idx: # if this option is the correct answer
                        # saves to CORRECT_ANSWER table
                        cursor.execute(
                            "INSERT INTO CORRECT_ANSWER (answerID, answer) VALUES (?, ?)",
                            (ans_id, opt_text)
                        )
                        # links the correct answer to this quiz and question
                        cursor.execute(
                            "INSERT INTO QUIZ (quizID, questionID, answerID) VALUES (?, ?, ?)",
                            (quiz_ID, q_id, ans_id)
                        )
                    else: # if this option is a wrong answer
                        # saves to WRONG_ANSWERS table instead
                        cursor.execute(
                            "INSERT INTO WRONG_ANSWERS (wrong_answerID, wrong_answer, questionID) VALUES (?, ?, ?)",
                            (ans_id, opt_text, q_id)
                        )
            conn.commit() # saves all changes to the database
            conn.close() # closes database connection
            flash("Multi-question quiz published! Members have 1 hour to complete it.", "success")
            return redirect(url_for('quiz_creation'))
        except Exception as e:
            print("ERROR during quiz creation:", e)
            flash(f"Error saving quiz: {e}", "danger")
            return redirect(url_for('quiz_creation'))

    # GET request - loads the page and fetches all previously created questions to display
    past_quizzes = []
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT question FROM QUESTIONS") # gets all past questions
        past_quizzes = [row[0] for row in cursor.fetchall()] # stores as a flat list of strings
        conn.close()
    except Exception as e:
        print("Error fetching past quizzes:", e)

    return render_template('quiz_creation.html', past_quizzes=past_quizzes) # loads the page with past quizzes    


@app.route('/add_member', methods=['GET', 'POST'])  # handles both loading the form and submitting it
def add_member():
    if not session.get('logged_in'):
        return redirect('/')
    if request.method == 'POST':
        number = request.form.get('number', '').strip()  # gets the student number and removes surrounding whitespace
        first = request.form.get('first', '').strip()  # gets the first name and removes surrounding whitespace
        last = request.form.get('last', '').strip()  # gets the last name and removes surrounding whitespace
        # makes sure all fields are filled before proceeding
        if not number or not first or not last:
            flash("All fields are required.", "danger")
            return render_template('attendance.html')
        try:
            conn = get_db()
            cursor = conn.cursor()
            # checks if member with this student number already exists
            cursor.execute("SELECT Student_number FROM MEMBER WHERE Student_number = ?", (number,))
            existing = cursor.fetchone()
            if existing:
                # blocks duplicate student numbers
                flash(f"A member with student number {number} already exists.", "danger")
                conn.close()
                return redirect(url_for('attendance'))
            # inserts the new member directly into the MEMBER table instead of members.csv
            cursor.execute(
                "INSERT INTO MEMBER (Student_number, Firstname, Lastname) VALUES (?, ?, ?)",
                (number, first, last)
            )
            conn.commit()
            conn.close()
            flash(f"Member {first} {last} added successfully.", "success")
            return redirect(url_for('attendance'))
        except Exception as e:
            print(f"Error adding member to database: {e}")
            flash("Failed to add member. Please try again.", "danger")
            return redirect(url_for('attendance'))
    return redirect(url_for('attendance'))


# shared function used for /report-page and /export-data --> gets the data 
def get_report_data():
    # set default values in case any queries fail
    total_members = 0
    active_this_month = 0
    avg_attendance_pct = 0
    total_points = 0
    top_earners = []
    recent_quizzes = []
    overall_part_rate = 0

    conn = None # set to None so it does not crash when the queries crash
    try:
        conn = get_db() # opens connection to the database
        cursor = conn.cursor() # creates cursor to run SQL queries
        try:
            # counts total number of members in the MEMBER table
            cursor.execute("SELECT COUNT(*) FROM MEMBER")
            row = cursor.fetchone()
            total_members = row[0] if row else 0 # defaults to 0 if no result

            # counts members who attended at least once this month
            cursor.execute("""
                SELECT COUNT(DISTINCT student_number)
                FROM ATTENDANCE
                WHERE strftime('%Y-%m', attendance_date) = strftime('%Y-%m', 'now')
            """)
            row = cursor.fetchone()
            active_this_month = row[0] if row else 0 # defaults to 0 if no result
        except sqlite3.OperationalError as e:
            # catches error if MEMBER or ATTENDANCE table doesn't exist
            print(f"Table missing (MEMBER/ATTENDANCE): {e}")

        try:
            # gets attendance per day
            cursor.execute("SELECT COUNT(*) FROM ATTENDANCE GROUP BY attendance_date")
            daily_counts = [r[0] for r in cursor.fetchall()]
            if daily_counts and total_members > 0:
                # calculates average daily attendance percentage
                avg_raw = sum(daily_counts) / len(daily_counts)  # averages the daily attendance counts
                avg_attendance_pct = int((avg_raw / total_members) * 100)
        except sqlite3.OperationalError as e:
            # catches error if ATTENDANCE table has issues
            print(f"Attendance table issue: {e}")

        try:
            # sums all points awarded since last Sunday
            cursor.execute("""
                SELECT SUM(number_points)
                FROM POINTS
                WHERE award_date >= date('now', 'weekday 0')
            """)
            row = cursor.fetchone()
            total_points = row[0] if row and row[0] else 0 # defaults to 0 if no points found
        except sqlite3.OperationalError as e:
            # catches error if POINTS table or award_date column is missing
            print(f"Points query failed: {e}")

        try:
            # gets top 5 members ranked by points earned this week
            cursor.execute("""
                SELECT m.Firstname, m.Lastname, COALESCE(SUM(p.number_points), 0) as total
                FROM MEMBER m
                LEFT JOIN POINTS p ON m.Student_number = p.student_number
                    AND p.award_date >= date('now', 'weekday 0')
                GROUP BY m.Student_number
                ORDER BY total DESC
                LIMIT 5
            """)
            top_earners = cursor.fetchall() # stores results as a list
        except sqlite3.OperationalError as e:
            # catches error if MEMBER or POINTS table is missing
            print(f"Top earners query failed: {e}")

        try:
            # gets the 3 most recent quizzes with their question text
            cursor.execute("""
                SELECT qst.question, q.quizID
                FROM QUIZ q
                JOIN QUESTIONS qst ON q.questionID = qst.questionID
                JOIN QUIZ_TIMERS qt ON q.quizID = qt.quizID
                ORDER BY qt.start_time DESC
                LIMIT 3
            """)
            for question_text, quiz_ID in cursor.fetchall(): # loops through each quiz
                # counts students who attempted this specific quiz
                cursor.execute("""
                    SELECT COUNT(DISTINCT student_number)
                    FROM QUIZ_ATTEMPTS
                    WHERE quizID = ?
                """, (quiz_ID,))
                attempts = cursor.fetchone()[0]
                # calculates participation rate
                part_rate = int((attempts / total_members) * 100) if total_members > 0 else 0
                # shortens titles when they are long
                short_title = (question_text[:40] + '...') if len(question_text) > 40 else question_text
                # appends quiz info as a dict, assigns CSS class based on participation rate
                recent_quizzes.append({
                    'title': short_title,
                    'rate': part_rate,
                    'bar_class': "excellent" if part_rate >= 80 else ("" if part_rate >= 50 else "warning")
                })
            # counts total students who attempted any quiz ever
            cursor.execute("SELECT COUNT(DISTINCT student_number) FROM QUIZ_ATTEMPTS")
            active_takers = cursor.fetchone()[0]
            # calculates overall participation rate across all quizzes
            overall_part_rate = int((active_takers / total_members) * 100) if total_members > 0 else 0
        except sqlite3.OperationalError as e:
            # catches error if QUIZ or QUIZ_ATTEMPTS tables don't exist yet
            print(f"Quiz tables missing: {e}")

    except sqlite3.Error as e:
        # catches any broader database connection errors
        print(f"Database connection error: {e}")
    finally:
        if conn:
            conn.close() # always closes the database connection when done

    # returns all collected data as a dictionary
    return {
        'total_members': total_members,
        'active_this_month': active_this_month,
        'avg_attendance_pct': avg_attendance_pct,
        'total_points': total_points,
        'top_earners': top_earners,
        'recent_quizzes': recent_quizzes,
        'overall_part_rate': overall_part_rate
    }


@app.route('/report-page')  # maps /report-page URL to this function
def report_page():
    if not session.get('logged_in'): # checks if user is logged in
        return redirect('/')
    data = get_report_data() # calls function to fetch all report data
    return render_template('report_page.html', **data) # unpacks dict and passes to HTML template


@app.route('/export-data')  # maps /export-data URL to this function
def export_data():
    if not session.get('logged_in'): # checks if user is logged in
        return redirect('/')
    # calls function and unpacks values from dict
    data = get_report_data()
    total_members      = data['total_members']
    active_this_month  = data['active_this_month']
    avg_attendance_pct = data['avg_attendance_pct']
    total_points       = data['total_points']
    top_earners        = data['top_earners']
    recent_quizzes     = data['recent_quizzes']
    overall_part_rate  = data['overall_part_rate']

    # creates an in-memory bytes buffer to write the PDF
    buffer = io.BytesIO()
    # sets up the PDF with letter size and margins
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    story = [] # list that holds all PDF elements in order

    # loads default styles for title, headings, and normal text
    styles = getSampleStyleSheet()
    title_style   = styles['Title']
    heading_style = styles['Heading2']
    normal_style  = styles['Normal']

    # adds report title and generation timestamp to the PDF
    story.append(Paragraph("Science Club Weekly Report", title_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    story.append(Spacer(1, 0.2 * inch)) # adds vertical spacing

    # builds the summary stats table data
    data_summary = [
        ["Metric", "Value"], # header row
        ["Total Members", total_members],
        ["Active This Month", active_this_month],
        ["Avg Attendance %", f"{avg_attendance_pct}%"],
        ["Total Points Awarded (This Week)", total_points],
        ["Overall Quiz Participation", f"{overall_part_rate}%"]
    ]
    # creates the table with set column widths
    table_summary = Table(data_summary, colWidths=[2.5*inch, 1.5*inch])
    # applies styling to the summary table
    table_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),       # grey header background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # white header text
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),                # left align all cells
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),    # bold header font
        ('FONTSIZE', (0, 0), (-1, 0), 12),                  # header font size
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),             # padding below header
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),     # beige body background
        ('GRID', (0, 0), (-1, -1), 1, colors.black)         # black grid lines
    ]))
    story.append(table_summary)
    story.append(Spacer(1, 0.3 * inch)) # adds vertical spacing

    # builds the top 5 earners table
    story.append(Paragraph("Top 5 Point Earners (This Week)", heading_style))
    data_top = [["Rank", "Name", "Points"]] # header row
    for idx, (first, last, pts) in enumerate(top_earners, 1): # loops through earners
        data_top.append([idx, f"{first} {last}", pts])
    if len(top_earners) == 0:
        data_top.append(["", "No data available", ""]) # safety if no earners

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
    story.append(Spacer(1, 0.3 * inch)) # adds vertical spacing

    # builds the recent quiz participation table
    story.append(Paragraph("Recent Quiz Participation", heading_style))
    data_quiz = [["Quiz Title", "Participation Rate"]] # header row
    for q in recent_quizzes: # loops through each quiz
        data_quiz.append([q['title'], f"{q['rate']}%"])
    if not recent_quizzes:
        data_quiz.append(["No quizzes published yet", ""]) # fallback if no quizzes

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

    doc.build(story) # builds the final PDF from all elements in story
    pdf_bytes = buffer.getvalue() # extracts the PDF bytes from the buffer
    buffer.close() # closes the buffer to free memory

    # sends the PDF as a downloadable file to the browser
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment;filename=club_report.pdf'}
    )


@app.route('/member-login', methods=['POST'])  # only accepts POST requests from the login form
def member_login():
    session.clear() # wipes existing attempts 
    # grabs student number and last name from html
    user_id = request.form.get('student_num', '').strip()
    user_last = request.form.get('last_name', '').strip().lower() 
    conn = None # make sure code doesn't crash since the connection was never opened 
    try:
        # checks if the user inputted last name and student number is found in the MEMBER table 
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Firstname, Student_number 
            FROM MEMBER 
            WHERE Student_number = ? AND LOWER(Lastname) = ?
        """, (user_id, user_last))  
        member = cursor.fetchone()

        if member:
            # lets them login
            session['logged_in'] = True
            session['first_name'] = str(member[0]).strip()  # stores the member's first name in the session
            session['student_id'] = user_id  # stores the student ID in the session for use across pages
            # fetches their points 
            cursor.execute(
                "SELECT SUM(number_points) FROM POINTS WHERE student_number = ?",
                (user_id,)
            )
            total_points = cursor.fetchone()[0]
            session['points'] = total_points or 0
            return redirect('/member-dashboard') # when found it takes them to the home page 
        else:
            # if not found it takes them back to login page 
            flash("Invalid Student Number or Last Name.", "danger")
            return redirect('/')
    except Exception as e:
        # catches unexpected errors that have occurred 
        print(f"Database Error: {e}")
        flash("Something went wrong. Please try again.", "danger")
        return redirect('/')
    finally:
        if conn:
            conn.close()
        # closes connection with database 


@app.route('/member-dashboard') 
def member_dashboard():
    if not session.get('logged_in'):
        return redirect('/')
    student_id = session.get('student_id')
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(number_points) FROM POINTS WHERE student_number = ?", (student_id,))
        total = cursor.fetchone()[0] or 0
        session['points'] = total  # refreshes the session points so the dashboard shows the latest value
        conn.close()
    except Exception as e:
        print(f"Error fetching points: {e}")
        session['points'] = 0  # defaults to 0 if the query fails so the page doesn't crash

    return render_template('member_dashboard.html')


@app.route('/attendance-form', methods=['GET', 'POST'])
def attendance_form():
    if not session.get('logged_in'):
        return redirect('/')

    if request.method == 'POST':
        coming_today = request.form.get('coming_today')  # gets the student's yes/no response from the form
        student_id = session.get('student_id')
        today_date = date.today().strftime("%Y-%m-%d")  # format date as YYYY-MM-DD for database 
        try:
            if coming_today == 'yes':
                conn = get_db()
                cursor = conn.cursor()
                # checks if attendance has already been recorded for this student today
                cursor.execute("""
                    SELECT 1 FROM ATTENDANCE 
                    WHERE student_number = ? AND attendance_date = ?
                """, (student_id, today_date))
                if cursor.fetchone():
                    # blocks duplicate attendance records for the same day
                    flash("You have already marked attendance today.", "info")
                else:
                    new_attendance_id = "ATT-" + str(uuid.uuid4())[:8]  # generates a unique ID for this attendance record
                    cursor.execute('''
                        INSERT INTO ATTENDANCE (attendanceID, student_number, attendance_date)
                        VALUES (?, ?, ?)
                    ''', (new_attendance_id, student_id, today_date))
                    conn.commit()
                    flash("See you :)", "success")
                conn.close()
            else:
                flash("Thanks for letting us know.", "info")
        except Exception as e:
            print(f"Database Error: {e}")
            flash("Oops! Something went wrong saving your attendance.", "danger")
            
        return redirect('/member-dashboard')
    return render_template('attendance_form.html')


@app.route('/quiz-taking', methods=['GET', 'POST'])  # handles both loading the quiz and submitting answers
def take_quiz():
    if not session.get('logged_in'): # checks if user is logged in
        return redirect('/')
    student_id = session.get('student_id') # gets the logged student's ID from session
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        # gets the most recently created quiz using rowid to find the latest entry
        cursor.execute("SELECT quizID, start_time FROM QUIZ_TIMERS ORDER BY rowid DESC LIMIT 1")
        latest_quiz = cursor.fetchone()
        # if no quiz exists at all, show an error
        if not latest_quiz:
            conn.close()
            return render_template('quiz_taking.html', error="No quiz currently available.")
        quiz_ID, start_str = latest_quiz  # unpacks the quiz ID and start time from the result
        start_time = datetime.fromisoformat(start_str) # converts stored string back to datetime
        # check the 1 hour window has passed since quiz was created
        if datetime.now() > start_time + timedelta(hours=1):
            conn.close()
            return render_template('quiz_taking.html', error="The time window for this quiz has expired!")    
        # check if student has already attempted this quiz
        cursor.execute("SELECT * FROM QUIZ_ATTEMPTS WHERE student_number=? AND quizID=?", (student_id, quiz_ID))
        if cursor.fetchone():
            conn.close()
            return render_template('quiz_taking.html', error="You have already completed this week's quiz!")
        # get all question IDs for this quiz once, used by both POST and GET below
        cursor.execute("SELECT questionID FROM QUIZ WHERE quizID=?", (quiz_ID,))
        question_ids = [row[0] for row in cursor.fetchall()]
        if request.method == 'POST': # runs when the student submits their answers
            score = 0  # starts the score at 0 and increments for each correct answer
            for q_id in question_ids:
                submitted = request.form.get(f'answer_{q_id}') # gets the student's selected answer
                # look up the correct answer for this question
                cursor.execute(
                    "SELECT answer FROM CORRECT_ANSWER WHERE answerID = "
                    "(SELECT answerID FROM QUIZ WHERE questionID=? AND quizID=?)",
                    (q_id, quiz_ID)
                )
                correct_row = cursor.fetchone()
                # add point if the submitted answer matches the correct answer
                if correct_row and submitted == correct_row[0]:
                    score += 1
            # record student has attempted the quiz so they can't retake it
            cursor.execute(
                "INSERT INTO QUIZ_ATTEMPTS (student_number, quizID) VALUES (?, ?)",
                (student_id, quiz_ID)
            )
            # only awards points if they got at least one question right
            if score > 0:
                cursor.execute(
                    "INSERT INTO POINTS (student_number, number_points, award_date) VALUES (?, ?, ?)",
                    (student_id, score, date.today())
                )
            conn.commit() # saves the attempt and points to the database
            conn.close()
            flash(f"Quiz submitted! You got {score}/{len(question_ids)} correct and earned {score} points.", "success")
            return redirect('/member-dashboard')
        # GET request - builds the quiz display data to show to the student
        quiz_data = []
        for q_id in question_ids:
            # gets the question text
            cursor.execute("SELECT question FROM QUESTIONS WHERE questionID=?", (q_id,))
            q_text = cursor.fetchone()[0]
            # gets the correct answer for this question
            cursor.execute("SELECT answer FROM CORRECT_ANSWER WHERE answerID IN (SELECT answerID FROM QUIZ WHERE questionID=?)", (q_id,))
            correct_ans = cursor.fetchone()[0]
            # gets 3 random wrong answers for this question
            cursor.execute("SELECT wrong_answer FROM WRONG_ANSWERS WHERE questionID=? ORDER BY RANDOM() LIMIT 3", (q_id,))
            wrong_options = [row[0] for row in cursor.fetchall()]
            # combine correct and wrong answers then shuffles so correct answer isn't always last
            options = wrong_options + [correct_ans]
            random.shuffle(options)
            quiz_data.append({'q_id': q_id, 'text': q_text, 'options': options})
        conn.close()
        return render_template('quiz_taking.html', quiz_data=quiz_data, quiz_id=quiz_ID)
    except Exception as e:
        # catch unexpected database errors
        print(f"Quiz taking error: {e}")
        if conn:
            conn.close()
        return render_template('quiz_taking.html', error="Something went wrong loading the quiz. Please try again.")


@app.route('/logout')  # maps /logout URL to this function
def logout():
    session.clear()  # removes all session data, effectively logging the user out
    flash("You have been logged out.", "info")
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)  # starts the Flask development server with debug mode on so errors show in the browser