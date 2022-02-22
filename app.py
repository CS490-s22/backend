from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
from db_cred import db #creds
from hashlib import sha1

app = Flask(__name__)

app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_pass']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/', methods=['GET'])
def start_app():
    return "Hello"
# User Login
@app.route('/validate_login', methods=['GET', 'POST'])
def validate_login():
    cur = mysql.connection.cursor()
    content_type = request.headers.get('Content-Type')
    if(content_type == 'application/json'):
        req = request.json
        username = req['user']
        password = sha1(req['password'].encode('utf-8')).hexdigest()
        rows = cur.execute("SELECT username, role FROM accounts WHERE username = '{0}' AND password = '{1}'".format(username, password))
        
        if rows > 0:
            result = cur.fetchall()[0]
            return jsonify(result)
        else:
            return jsonify(error='Invalid Credentials')
    else:
        return jsonify(error = "Content-Type not supported | Request must in JSON format")

# Teacher Functinalities

# Add Question to Question Bank
@app.route('/new_question', method=['POST'])
def insert_new_question():
    cur = mysql.connection.cursor()
    content_type = request.headers.get('Content-Type')
    if(content_type == 'application/json'):
        req = request.json
        question = req['title']
        result = cur.execute("".format(question))

        return jsonify(response="200")
    else:
        return jsonify(error = "Content-Type not supported | Request must in JSON format")


if __name__ == '__main__':
    app.run(host='0.0.0.0')
