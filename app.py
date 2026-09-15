from flask import Flask, render_template, request, redirect, session, send_file, flash
import sqlite3
import os

from werkzeug.utils import secure_filename

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors


app = Flask(__name__)

app.secret_key = "student_secret_key"

app.config["UPLOAD_FOLDER"] = "static/uploads"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# --------------------------------------------------
# SAVE FILE
# --------------------------------------------------

def save_file(file):

    if file and file.filename != "":

        filename = secure_filename(file.filename)

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(filepath)

        return filename

    return None


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def create_database():

    conn = sqlite3.connect("students.db")
    cur = conn.cursor()

    # Admin table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    # Students table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        roll TEXT,
        department TEXT,
        year TEXT,
        gender TEXT,
        phone TEXT,
        email TEXT,
        photo TEXT
    )
    """)

    # Add marksheet columns if they don't already exist
    cur.execute("PRAGMA table_info(students)")
    existing_columns = [row[1] for row in cur.fetchall()]

    marksheet_columns = [
        "tenth_marksheet",
        "eleventh_marksheet",
        "twelfth_marksheet",
        "sem1_marksheet",
        "sem2_marksheet",
        "sem3_marksheet",
        "sem4_marksheet",
        "sem5_marksheet",
        "sem6_marksheet"
    ]

    for column in marksheet_columns:

        if column not in existing_columns:

            cur.execute(
                f"ALTER TABLE students ADD COLUMN {column} TEXT"
            )

    # Create default admin
    cur.execute("SELECT * FROM admin")

    if cur.fetchone() is None:

        cur.execute(
            "INSERT INTO admin(username,password) VALUES(?,?)",
            ("admin", "1234")
        )

    conn.commit()
    conn.close()


# --------------------------------------------------
# HOME / LOGIN
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("students.db")
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM admin
            WHERE username=? AND password=?
            """,
            (username, password)
        )

        admin = cur.fetchone()

        conn.close()

        if admin:

            session["admin"] = username

            return redirect("/dashboard")

        else:

            return "Invalid Username or Password"

    return render_template("home.html")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/")

    conn = sqlite3.connect("students.db")
    cur = conn.cursor()

    # Total students
    cur.execute("SELECT COUNT(*) FROM students")

    total_students = cur.fetchone()[0]

    # Department wise
    cur.execute("""
        SELECT department, COUNT(*)
        FROM students
        GROUP BY department
        ORDER BY department
    """)

    department_data = cur.fetchall()

    # Gender wise
    cur.execute("""
        SELECT gender, COUNT(*)
        FROM students
        GROUP BY gender
        ORDER BY gender
    """)

    gender_data = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        department_data=department_data,
        gender_data=gender_data
    )


# --------------------------------------------------
# ADD STUDENT
# --------------------------------------------------

@app.route("/addstudent", methods=["GET", "POST"])
def addstudent():

    if "admin" not in session:
        return redirect("/")

    if request.method == "POST":

        name = request.form["name"]
        roll = request.form["roll"]
        department = request.form["department"]
        year = request.form["year"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]

        photo = request.files.get("photo")

        filename = save_file(photo)

        conn = sqlite3.connect("students.db")
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO students
        (
            name,
            roll,
            department,
            year,
            gender,
            phone,
            email,
            photo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            roll,
            department,
            year,
            gender,
            phone,
            email,
            filename
        ))

        conn.commit()
        conn.close()

        flash("Student added successfully!")

        return redirect("/viewstudents")

    return render_template("addstudent.html")


# --------------------------------------------------
# VIEW STUDENTS
# --------------------------------------------------

@app.route("/viewstudents")
def viewstudents():

    if "admin" not in session:
        return redirect("/")

    conn = sqlite3.connect("students.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM students")

    students = cur.fetchall()

    conn.close()

    return render_template(
        "viewstudents.html",
        students=students
    )


# --------------------------------------------------
# SEARCH STUDENT
# --------------------------------------------------

@app.route("/search")
def search():

    if "admin" not in session:
        return redirect("/")

    value = request.args.get("search", "")
    department = request.args.get("department", "")
    year = request.args.get("year", "")
    gender = request.args.get("gender", "")

    conn = sqlite3.connect("students.db")
    cur = conn.cursor()

    query = """
        SELECT * FROM students
        WHERE (name LIKE ? OR roll LIKE ?)
    """

    params = [
        "%" + value + "%",
        "%" + value + "%"
    ]

    if department:
        query += " AND department = ?"
        params.append(department)

    if year:
        query += " AND year = ?"
        params.append(year)

    if gender:
        query += " AND gender = ?"
        params.append(gender)

    cur.execute(query, params)

    students = cur.fetchall()

    conn.close()

    return render_template(
        "viewstudents.html",
        students=students
    )


# --------------------------------------------------
# UPDATE STUDENT
# --------------------------------------------------

@app.route("/update/<int:id>", methods=["GET", "POST"])
def update_student(id):

    if "admin" not in session:
        return redirect("/")

    conn = sqlite3.connect("students.db")
    cur = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        roll = request.form["roll"]
        department = request.form["department"]
        year = request.form["year"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]

        cur.execute("""
        UPDATE students SET
            name=?,
            roll=?,
            department=?,
            year=?,
            gender=?,
            phone=?,
            email=?
        WHERE id=?
        """,
        (
            name,
            roll,
            department,
            year,
            gender,
            phone,
            email,
            id
        ))

        conn.commit()
        conn.close()

        flash("Student updated successfully!")

        return redirect("/viewstudents")

    cur.execute(
        "SELECT * FROM students WHERE id=?",
        (id,)
    )

    student = cur.fetchone()

    conn.close()

    return render_template(
        "update.html",
        student=student
    )


# --------------------------------------------------
# STUDENT PROFILE
# --------------------------------------------------

@app.route("/profile/<int:id>")
def profile(id):

    if "admin" not in session:
        return redirect("/")

    conn = sqlite3.connect("students.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM students WHERE id=?",
        (id,)
    )

    student = cur.fetchone()

    conn.close()

    return render_template(
        "profile.html",
        student=student
    )


# --------------------------------------------------
# DELETE STUDENT
# --------------------------------------------------

@app.route("/delete/<int:id>")
def delete_student(id):

    if "admin" not in session:
        return redirect("/")

    conn = sqlite3.connect("students.db")
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM students WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Student deleted successfully!")

    return redirect("/viewstudents")


# --------------------------------------------------
# STUDENT MARKSHEET UPLOAD
# PUBLIC LINK FOR STUDENTS
# --------------------------------------------------

@app.route("/studentupload", methods=["GET", "POST"])
def studentupload():

    if request.method == "POST":

        roll = request.form["roll"]

        conn = sqlite3.connect("students.db")
        cur = conn.cursor()

        # Check roll number
        cur.execute(
            "SELECT id FROM students WHERE roll=?",
            (roll,)
        )

        student = cur.fetchone()

        if student is None:

            conn.close()

            return """
            <h2 style="text-align:center;color:red;">
            Roll Number not found!
            </h2>

            <p style="text-align:center;">
            Please enter a valid Roll Number.
            </p>

            <div style="text-align:center;">
            <a href="/studentupload">Go Back</a>
            </div>
            """

        # Get uploaded files
        tenth = request.files.get("tenth_marksheet")
        eleventh = request.files.get("eleventh_marksheet")
        twelfth = request.files.get("twelfth_marksheet")

        sem1 = request.files.get("sem1_marksheet")
        sem2 = request.files.get("sem2_marksheet")
        sem3 = request.files.get("sem3_marksheet")
        sem4 = request.files.get("sem4_marksheet")
        sem5 = request.files.get("sem5_marksheet")
        sem6 = request.files.get("sem6_marksheet")

        # Save files
        tenth_file = save_file(tenth)
        eleventh_file = save_file(eleventh)
        twelfth_file = save_file(twelfth)

        sem1_file = save_file(sem1)
        sem2_file = save_file(sem2)
        sem3_file = save_file(sem3)
        sem4_file = save_file(sem4)
        sem5_file = save_file(sem5)
        sem6_file = save_file(sem6)

        # Update only uploaded files
        if tenth_file:
            cur.execute(
                "UPDATE students SET tenth_marksheet=? WHERE roll=?",
                (tenth_file, roll)
            )

        if eleventh_file:
            cur.execute(
                "UPDATE students SET eleventh_marksheet=? WHERE roll=?",
                (eleventh_file, roll)
            )

        if twelfth_file:
            cur.execute(
                "UPDATE students SET twelfth_marksheet=? WHERE roll=?",
                (twelfth_file, roll)
            )

        if sem1_file:
            cur.execute(
                "UPDATE students SET sem1_marksheet=? WHERE roll=?",
                (sem1_file, roll)
            )

        if sem2_file:
            cur.execute(
                "UPDATE students SET sem2_marksheet=? WHERE roll=?",
                (sem2_file, roll)
            )

        if sem3_file:
            cur.execute(
                "UPDATE students SET sem3_marksheet=? WHERE roll=?",
                (sem3_file, roll)
            )

        if sem4_file:
            cur.execute(
                "UPDATE students SET sem4_marksheet=? WHERE roll=?",
                (sem4_file, roll)
            )

        if sem5_file:
            cur.execute(
                "UPDATE students SET sem5_marksheet=? WHERE roll=?",
                (sem5_file, roll)
            )

        if sem6_file:
            cur.execute(
                "UPDATE students SET sem6_marksheet=? WHERE roll=?",
                (sem6_file, roll)
            )

        conn.commit()
        conn.close()

        return """
        <div style="text-align:center;margin-top:100px;">
            <h2 style="color:green;">
                ✅ Marksheets Uploaded Successfully!
            </h2>

            <p>Your marksheets have been submitted.</p>

            <a href="/studentupload">
                Upload Again
            </a>
        </div>
        """

    return render_template("studentupload.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.pop("admin", None)

    return redirect("/")


# --------------------------------------------------
# DOWNLOAD PDF
# --------------------------------------------------

@app.route("/downloadpdf")
def downloadpdf():

    if "admin" not in session:
        return redirect("/")

    conn = sqlite3.connect("students.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT id,name,roll,department,year,gender,phone,email
    FROM students
    """)

    students = cur.fetchall()

    conn.close()

    data = [
        [
            "ID",
            "Name",
            "Roll",
            "Department",
            "Year",
            "Gender",
            "Phone",
            "Email"
        ]
    ]

    for student in students:
        data.append(list(student))

    pdf_path = "students_report.pdf"

    pdf = SimpleDocTemplate(pdf_path)

    table = Table(data)

    table.setStyle(
        TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("ALIGN", (0,0), (-1,-1), "CENTER")
        ])
    )

    pdf.build([table])

    return send_file(
        pdf_path,
        as_attachment=True
    )


# --------------------------------------------------
# CREATE DATABASE
# --------------------------------------------------

create_database()


# --------------------------------------------------
# RUN
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )