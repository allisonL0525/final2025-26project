# pls don't die
print("Hello!")

from flask import Flask, render_template, request, redirect, session, flash
import csv # Make sure this is at the top of app.py



app = Flask(__name__)
app.secret_key = "super_secret_science_key" 

# --- ALL ROUTES GO HERE ---

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
        # 1. Store the error message in the "flash" memory
        flash("Invalid Username or Password.", "danger")
        # 2. Tell the browser to go back to the home page (login.html)
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
    return render_template('master_point_tracker.html')

@app.route('/modify-data')
def modify_data():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template('modify_data.html')


@app.route('/attendance')
def attendance():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template('attendance.html')

@app.route('/quiz-creation')
def quiz_creation():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template('quiz_creation.html')

@app.route('/report-page')
def report_page():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template('report_page.html')


# --- MEMBER SECTION ---
@app.route('/member-login', methods=['POST'])
def member_login():
    session.clear() 
    
    # 1. Grab what the HTML form sent
    user_id = request.form.get('student_num', '').strip()
    user_last = request.form.get('last_name', '').strip().lower()

    debug_text = f"<h3>Diagnostic Mode</h3>"
    debug_text += f"<p><b>1. Your HTML form sent:</b> Student ID = '{user_id}', Last Name = '{user_last}'</p>"

    try:
        with open('members.csv', mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            debug_text += f"<p><b>2. CSV Headers found:</b> {reader.fieldnames}</p>"
            debug_text += "<p><b>3. Scanning CSV Rows:</b></p><ul>"
            
            for row in reader:
                csv_id = str(row.get('Student_number', '')).strip()
                csv_last = str(row.get('Lastname', '')).strip().lower()
                
                debug_text += f"<li>Checking against CSV row -> ID: '{csv_id}', Last Name: '{csv_last}'</li>"

                # If it finds a match, it logs you in!
                if csv_id == user_id and csv_last == user_last:
                    session['logged_in'] = True
                    session['first_name'] = str(row.get('Firstname', 'Member')).strip()
                    session['student_id'] = csv_id
                    session['points'] = row.get('Points', 0)
                    return redirect('/member-dashboard')
            
            # If it finishes the loop with no match, show the report card
            debug_text += "</ul><p style='color:red;'><b>RESULT: No match found!</b> Look at the lists above. What doesn't match?</p>"
            return debug_text

    except Exception as e:
        return f"<h3>CRITICAL ERROR!</h3><p>Python says: {e}</p><p>Do you actually have a file named <b>members.csv</b> in your project folder, or are you using a database file (like .db)?</p>"

@app.route('/member-dashboard')
def member_dashboard():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template('member_dashboard.html')

@app.route('/my-points')
def my_points():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template('my_points.html')


@app.route('/logout')
def logout():
    session.clear() # This deletes "Member/NA" from your browser
    flash("You have been logged out.", "info")
    return redirect('/') # Sends you back to the login page


# --- START BUTTON AT THE VERY END ---
if __name__ == "__main__":
    app.run(debug=True)