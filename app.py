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


@app.route('/', methods=['GET', 'POST'])
def start_app():
    return "Hello"
# User Login
@app.route('/validate_login', methods=['GET', 'POST'])
def validate_login():
    cur = mysql.connection.cursor()
    content_type = request.headers.get('Content-Type')
    if(content_type == 'application/json'):
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
    

# Teacher Functinalities

# Retreive Question Bank or questions based on request method
@app.route('/question_bank', methods=['GET','POST'])
def retreive_questions():
    cur = mysql.connection.cursor()
    if request.method == "GET":
        rows = cur.execute("SELECT * FROM questions")
        if rows > 0:
            result = cur.fetchall()
            return jsonify(result)
    elif request.method == "POST":
        return jsonify(error="POST Request for this endpoint not implemented yet")
    else:
        return jsonify(erorr="Howdidyougethere?")
    

if __name__ == '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.run(host='0.0.0.0')
