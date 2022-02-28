from flask import Blueprint, jsonify, request, current_app as app
from database import mysql
import logging

questions = Blueprint("questions",__name__)


# -----------------------
# TEACHER FUNCTIONALITIES
# -----------------------
# Retreive Question Bank or questions based on request method
@questions.route('/question_bank', methods=['GET','POST'])
def retreive_questions():
    cur = mysql.connection.cursor()
    if request.method == "GET":
        rows = cur.execute("SELECT id, title, topics AS 'category', question AS description, difficulty, madeby FROM questions ORDER BY id DESC")
        if rows > 0:
            result = cur.fetchall()
            return jsonify(result)
    elif request.method == "POST":
        content_type = request.headers.get('Content-Type')
        if content_type == "application/json":
            req = request.json
            limit = req['limit']
            rows = cur.execute(f"SELECT id, title, topics AS 'category', question AS description, difficulty, madeby FROM questions ORDER BY id DESC LIMIT {limit}")
            if rows > 0:
                result = cur.fetchall()
            return jsonify(result)
        else:
            return jsonify(error = "Content-Type not supported | Request must be in JSON format"), 400
    else:
        return jsonify(error="Howdidyougethere?"), 400

#Insert new question into question bank
@questions.route('/new_question', methods=['POST'])
def insert_new_question():
    cur = mysql.connection.cursor()
    if request.method != 'POST':
        return jsonify(error="REQUIRES POST REQUEST")
    
    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        title = req['title']
        topic = req['category']
        difficulty = req['difficulty']
        question = req['description']
        madeby = req['professorID']
        testcases = req['testCases']

        rows_affected = cur.execute("INSERT INTO questions(id, title, topics, question, difficulty, madeby) VALUES(null,\"{}\",\"{}\",\"{}\",\"{}\",{})".format(title,topic,question,difficulty,madeby))
        mysql.connection.commit()
        logging.warn("ROWS INSERTED INTO QUESTIONS: %d", rows_affected)

        cur.execute("SELECT MAX(id) as id FROM questions")
        question_id = cur.fetchall()[0]['id']
        
        for case in testcases:
            caseI = case['functionCall']
            caseO = case['expectedOutput']
            output_type = case['type']
            rows_affected = cur.execute("INSERT INTO testcases(id, qid, input, output,outputtype) VALUES(null,{},'{}','{}','{}')".format(question_id,caseI,caseO,output_type))
            mysql.connection.commit()
            logging.warn("ROWS INSERTED INTO TESTCASES: %d", rows_affected)
        
        return jsonify(questionID = question_id), 201
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400