from lib2to3.pgen2.tokenize import StopTokenizing
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import sqlite3 
import smtplib


from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret"  # Change this
jwt = JWTManager(app)

app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_PATH'] = 'uploads'



def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# get the connection to the sqlite database
def get_db() -> sqlite3.Connection:
    db = sqlite3.connect('database.db')
    db.row_factory = dict_factory

    cursor = db.cursor()
    
    # create user table if it doesn't exist
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)")
    

    
    # create a students table if it doesn't exist 
    # table contains the student's name, id, mobile, email, blood, status (default pending) and studentId
    cursor.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, studentId TEXT, mobile TEXT, email TEXT, blood TEXT, status TEXT default 'pending', profileImageName TEXT, IdProofImage TEXT, memoImage TEXT, allotmentImage TEXT, reason TEXT default '')")
    
    return db

# check if the user credentials are in the database
# if so, return the user id
def check_user(username, password):
    db = get_db()
    cur = db.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    return cur.fetchone()

# get all students details from the database where status is pending
def get_pending_students():
    db = get_db()
    cur = db.execute("SELECT * FROM students WHERE status = 'pending'")
    return cur.fetchall()


# get all students details from the database where status is approved
def get_approved_students():
    db = get_db()
    cur = db.execute("SELECT * FROM students WHERE status = 'approved'")
    return cur.fetchall()

# get all students details from the database where status is rejected
def get_rejected_students():
    db = get_db()
    cur = db.execute("SELECT * FROM students WHERE status = 'rejected'")
    return cur.fetchall()


# check if the student id is already in the database
def check_student_id(studentId):
    db = get_db()
    cur = db.execute("SELECT * FROM students WHERE studentId = ?", (studentId,)).fetchone()
    db.close()
    if cur:
        return True
    

# get student details from the database where the student id is equal to the student id
def get_student(studentId):
    db = get_db()
    cur = db.execute("SELECT * FROM students WHERE studentId = ?", (studentId,))
    return cur.fetchone()

def update_status(studentId: str, status: str) -> None:
    db = get_db()
    cur = db.execute("UPDATE students SET status = ? WHERE studentId = ?", (status, studentId))
    db.commit()

def check_student_id_exists(studentId, cursor):
    return list(cursor.execute("SELECT * FROM students WHERE studentId = ?", (studentId,)))
    

# add student details to the database
def add_student(name: str, studentId: str, mobile: str, email: str, blood: str, filename: str, idProof: str, allotment: str, memo: str) -> None:
    db = get_db()
    status = check_student_id_exists(studentId, db.cursor())
    if (status):
        if status[0].status == "rejected":    
            db.execute("INSERT INTO students (name, studentId, mobile, email, blood, profileImageName, IdProofImage, allotmentImage, memoImage) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (name, studentId, mobile, email, blood, filename, idProof, allotment, memo))
            db.commit()
            db.close()
            update_status(studentId, 'pending')
        return 
    db.execute("INSERT INTO students (name, studentId, mobile, email, blood,profileImageName, idProofImage,allotmentImage, memoImage) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (name, studentId, mobile, email, blood, filename, idProof, allotment, memo))
    db.commit()


def update_reason(studentId: str, reason: str) -> None:
    db = get_db()
    cur = db.execute("UPDATE students SET reason = ? WHERE studentId = ?", (reason, studentId))
    db.commit()



# function to create a fake user for testing purposes
# username : test and password : test
def create_fake_user():
    db = get_db()
    db.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("test", "test"))
    db.commit()

@app.route("/login", methods=["POST", "OPTIONS"])
def login():

    # if request is for options, return 200
    if request.method == "OPTIONS":
        # set headers to allow cross origin resource sharing
        # set Access-Control-Allow-Headers to allow the header to be sent
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return response
        
    
    if not request.is_json:
        response = jsonify({"msg": "Missing JSON in request"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 400
    
    
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    
    user_id = check_user(username, password)
    if not user_id:
        response = jsonify({"msg": "Bad username or password"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 401        
    
    access_token = create_access_token(identity=user_id)
    response = jsonify({"access_token":access_token})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response, 200
    

@app.route("/files/<img_name>")
def get_file(img_name: str):
    """Download a file."""
    UPLOAD_DIRECTORY = app.config['UPLOAD_PATH']
    resp = send_from_directory(UPLOAD_DIRECTORY, img_name, as_attachment=True)
    resp.headers.add("Access-Control-Allow-Origin", "*")
    resp.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    return resp
    
@app.route("/dashboard", methods=["GET", "OPTIONS"])
@jwt_required()
def dashboard():
    # if request is for options, return 200
    if request.method == "OPTIONS":
        # set headers to allow cross origin resource sharing
        # set Access-Control-Allow-Headers to allow the header to be sent
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return response
    
    # get all the accepted, pending and rejected students
    # format {accepted: [], pending: [], rejected: []}
    accepeted = get_approved_students()
    pending = get_pending_students()
    rejected  = get_rejected_students()
    img_url = "http://localhost:5000/files/"
    # update the profileImageName key in accepted, pending and rejected students
        
    
    accepeted = [{**student, "profileImageName": img_url + student["profileImageName"], "memo": img_url + student["memoImage"], "allotment": student["allotmentImage"], "proof": student["IdProofImage"]} for student in accepeted]
    pending = [{**student, "profileImageName": img_url + student["profileImageName"],"memo": img_url + student["memoImage"], "allotment": img_url + student["allotmentImage"], "proof": img_url +  student["IdProofImage"]} for student in pending]
    rejected = [{**student, "profileImageName": img_url + student["profileImageName"]} for student in rejected]
    print(pending)
    students = {
        "accepted": accepeted,
        "pending": pending,
        "rejected": rejected
    }
    
    response = jsonify(students)
    response.headers.add("Access-Control-Allow-Origin", "*")
    
    # return the students in the format 
    return response, 200



# create a new student route
# get all the details from the request
@app.route("/student", methods=["POST"])
def create_student():
    # get the data from the form and store it in variables (name, studentId, mobile, email, blood)
    name = request.form.get("name", None)
    student_id = request.form.get("id", "0000")
    email_id = request.form.get("email", None)
    blood = request.form.get("blood_group", None)
    mobile = request.form.get("mobile", None)
    # check if the student id is already in the database
    
    if check_student_id(student_id):
        response = jsonify({"msg": "Student id already exists"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 400
    
    # get the file from the form and save it in a folder
    print(request.files)
    uploaded_file = request.files['profile-image']
    id_proof = request.files["id-proof"]
    allotment_order = request.files["allotment-order"]
    memo = request.files["10-memo"]
    
    profile_filename = student_id + "_profile_." + uploaded_file.filename.split(".")[-1]
    idProof_filename = student_id + "_idproof_." + id_proof.filename.split(".")[-1]
    allotment_filename = student_id + "_allOrder_." + allotment_order.filename.split(".")[-1]
    memo_filename = student_id + "_memo_." + memo.filename.split(".")[-1]
    
    
    uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], profile_filename))
    id_proof.save(os.path.join(app.config['UPLOAD_PATH'], idProof_filename))
    allotment_order.save(os.path.join(app.config['UPLOAD_PATH'], allotment_filename))
    memo.save(os.path.join(app.config['UPLOAD_PATH'], memo_filename))


    # check if details are valid
    if not student_id or not name or not blood or not mobile or not email_id:
        print(student_id, name, blood, mobile, email_id)
        return jsonify({"msg": "Please provide all the details"}), 400
    
   
    # add the student to the database
    add_student(name, student_id, mobile, email_id, blood, profile_filename, idProof_filename, allotment_filename, memo_filename)
    response = jsonify({"msg": "Added Successfully"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 200

# approve student idCard
@app.route("/approve/<student_id>", methods=["GET", "OPTIONS"])
def approve_student_status(student_id: str):
    if request.method == "OPTIONS":
        # set headers to allow cross origin resource sharing
        # set Access-Control-Allow-Headers to allow the header to be sent
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return response
    
    status = "accepted"
    update_status(student_id, status)
    student = get_student(student_id)
    send_mail(status, student_id,student["name"], student["email"])
    response = jsonify({"msg": "Students Status Updated"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 200


@app.route("/reject/<student_id>", methods=["GET", "OPTIONS"])
def reject_student_status(student_id: str):
    if request.method == "OPTIONS":
        # set headers to allow cross origin resource sharing
        # set Access-Control-Allow-Headers to allow the header to be sent
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return response

    reason = request.args.get("reason", None)
    status = "rejected"
    update_status(student_id, status)
    student = get_student(student_id)
    update_reason(student_id, reason)
    send_mail(status, student_id,student["name"], student["email"], reason)
    response = jsonify({"msg": "Students Status Updated"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response, 200
    
    
@app.route("/idcard/<student_id>", methods=["GET", "OPTIONS"])
def get_id_card(student_id: str):
    if request.method == "OPTIONS":
        # set headers to allow cross origin resource sharing
        # set Access-Control-Allow-Headers to allow the header to be sent
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return response
    student = get_student(student_id)
    response = jsonify(student)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response, 200
    

def send_mail(status : str, student_id: str, name: str, email_: str, reason: str = ""):
    from_ = "vijaysaivamsi0@gmail.com"
    to = email_
    pwd = "pkzjvabbclcfoqtm"
    if status == "accepted":
        subject = "Your ID Card has been approved"
        body = "Dear " + name + ",\n\nYour ID Card has been approved.\n\nRegards,\n\nSVIT.\nYou can download your ID Card from the link below.\n\nhttp://localhost:3000/idcard/" + student_id
    else:
        subject = "Your ID Card has been rejected"
        body = "Dear " + name + f",\n\nYour ID Card has been rejected.\n\nRegards,\n\nSVIT.\nReason: {reason}"
    
    message = "Subject: {}\n\n{}".format(subject, body)
    
    # connect to the server
    conn = smtplib.SMTP('smtp.gmail.com', 587)
    
    # start TLS for security
    conn.starttls()
    
    # login to the server
    conn.login(from_, pwd)
    
    # send the mail
    conn.sendmail(from_, to, message)
    
    # close the connection
    conn.close()


if __name__ == "__main__":
    app.run(debug=True)
    # create_fake_user()