from flask import Flask, jsonify, request
from numpy import diff
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


@app.route('/', methods=['GET', 'POST'])
def start_app():
    return "Nothin here"


# User Login
@app.route('/validate_login', methods=['GET', 'POST'])
def validate_login():
    cur = mysql.connection.cursor()
    content_type = request.headers.get('Content-Type')
    if request.method is not 'POST':
        return jsonify(error="REQUIRES POST REQUEST")
    if content_type is 'application/json':
        req = request.json
        username = req['username']
        password = sha1(req['password'].encode('utf-8')).hexdigest()
        rows = cur.execute("SELECT username, role FROM users WHERE username = '{0}' AND password = '{1}'".format(username, password))
        
        if rows > 0:
            result = cur.fetchall()[0]
            return jsonify(result)
        else:
            return jsonify(error='Invalid Credentials')
    else:
        return jsonify(error = "Content-Type not supported | Request must be in JSON format")
    
# -----------------------
# TEACHER FUNCTIONALITIES
# -----------------------
# Retreive Question Bank or questions based on request method
@app.route('/question_bank', methods=['GET','POST'])
def retreive_questions():
    cur = mysql.connection.cursor()
    if request.method is "GET":
        rows = cur.execute("SELECT * FROM questions")
        if rows > 0:
            result = cur.fetchall()
            return jsonify(result)
    elif request.method is "POST":
        return jsonify(error="POST Request for this endpoint not implemented yet")
    else:
        return jsonify(erorr="Howdidyougethere?")

#Insert new question into question bank
@app.route('new_question', methods=['POST'])
def insert_new_question():
    cur = mysql.connection.cursor()
    if request.method is not 'POST':
        return jsonify(error="REQUIRES POST REQUEST")
    
    content_type = request.headers.get("Content-Type")
    if content_type is 'application\json':
        req = request.json
        title = req['title']
        topic = req['topic']
        difficulty = req['difficulty']
        question = req['description']
        madeby = req['creatorid']
        testcases = req['testcases']

        rows_affected = cur.execute("INSERT INTO questions(id, title, topics, question, difficulty, madeby) VALUES(null,'{}','{}','{}''{}','{}')".format(title,topic,question,difficulty,madeby))
        mysql.connection.commit()
        logging.warn("ROWS INSERTED INTO QUESTIONS: %d", rows_affected)

        rows = cur.execute("SELECT MAX(id) as id FROM questions;")
        if rows == 1:
            question_id = cur.fetchall()[0]['id']
        for case in testcases:
            caseI = case['input']
            caseO = case['output']
            cur.execute("INSERT INTO cases(id, qid, input, output) VALUES(null,{},'{}','{}')".format(question_id,caseI,caseO))
        
        return jsonify(result="200", questionID = question_id)
    else:
        return jsonify(error="JSON FORMAT REQUIRED")





    


if __name__ == '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.run(host='0.0.0.0')
