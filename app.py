import json
from questions import questions
from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
from db_cred import db #creds
from hashlib import sha1
import logging

app = Flask(__name__)

app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_pass']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

app.register_blueprint(questions)

@app.route('/', methods=['GET', 'POST'])
def start_app():
    return "Nothin here"


# User Login
@app.route('/validate_login', methods=['GET', 'POST'])
def validate_login():
    cur = mysql.connection.cursor()
    content_type = request.headers.get('Content-Type')
    if request.method != 'POST':
        return jsonify(error="REQUIRES POST REQUEST")
    if content_type == 'application/json':
        req = request.json
        username = req['username']
        password = sha1(req['password'].encode('utf-8')).hexdigest()
        rows = cur.execute("SELECT username, role FROM users WHERE username = '{0}' AND password = '{1}'".format(username, password))
        
        if rows > 0:
            result = cur.fetchall()[0]
            user_role = result['role']

            if user_role == "Student":
                cur.execute("SELECT id, firstname, lastname FROM students WHERE username = '{0}' ".format(username)) 
                res = cur.fetchall()[0]
            elif user_role == "Professor":
                cur.execute("SELECT id, firstname, lastname FROM professors WHERE username = '{0}' ".format(username)) 
                res = cur.fetchall()[0]

            return jsonify(role=user_role, lastName=res['lastname'], firstName=res['firstname'], id=res['id'], username=username)
        else:
            return jsonify(error='Invalid Credentials')
    else:
        return jsonify(error = "Content-Type not supported | Request must be in JSON format")
    

#Create new exam
@app.route('/new_exam',methods=['POST'])
def insert_new_exam():
    cur = mysql.connection.cursor()
    if request.method != 'POST':
        return jsonify(error="REQUIRES POST REQUEST")

    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        name = req['name']
        details = req['details']
        madeby = req['professorID']
        cur.execute("INSERT INTO exams(id, name, details, madeby) VALUES(null,\"{}\",\"{}\",\"{}\")".format(name, details, madeby))
        mysql.connection.commit()
        cur.execute("SELECT MAX(id) AS id FROM exams")
        result = cur.fetchall()[0]['id']
        return jsonify(result="OK", examID=result)
    else:
        return jsonify(error="JSON FORMAT REQUIRED")

if __name__ == '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.run(host="0.0.0.0")
    #app.run(debug=True)
