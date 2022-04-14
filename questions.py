from flask import Blueprint, jsonify, request, current_app as app
from database import mysql
from flask_cors import cross_origin
import logging

questions = Blueprint("questions",__name__)

# Retreive Question Bank or questions based on request method
@questions.route('/question_bank', methods=['GET','POST'])
@cross_origin(allow_headers=['Content-Type'])
def retreive_questions():
    logging.getLogger('flask_cors').level = logging.DEBUG
    cur = mysql.connection.cursor()
    if request.method == "GET":
        rows = cur.execute("""SELECT id, title, topics AS 'category', question AS description, difficulty, madeby 
                              FROM questions
                              ORDER BY id DESC""")
        if rows > 0:
            result = cur.fetchall()
        else:
            result = {"error":"No questions found..."}
        return jsonify(result)
    elif request.method == "POST":
        content_type = request.headers.get('Content-Type')
        if content_type == "application/json":
            req = request.json
            conditions = [req['search'], req['search'], req['stype'], req['category'], req['stype'], req['difficulty'], req['limit']]
            
            for i in range(len(conditions)):
                conditions[0] = f"%{conditions[0]}%"
                
            query = """SELECT id, title, topics AS 'category', question AS description, difficulty, madeby 
                       FROM questions 
                       WHERE (title LIKE %s OR question LIKE %s) %s topics LIKE %s %s difficulty LIKE %s
                       ORDER BY id DESC
                       LIMIT %s"""
            conditions = tuple(conditions)
            print(conditions, " ", (query % conditions))
            rows = cur.execute("""SELECT id, title, topics AS 'category', question AS description, difficulty, madeby 
                                  FROM questions 
                                  WHERE (title LIKE %s OR question LIKE %s) %s topics LIKE %s %s difficulty LIKE %s
                                  ORDER BY id DESC 
                                  LIMIT %s""", conditions)
            if rows > 0:
                result = cur.fetchall()
            else: 
                result = {"error":"No questions found..."}
            return jsonify(result)
        else:
            return jsonify(error = "Content-Type not supported | Request must be in JSON format"), 400
    else:
        return jsonify(error="Howdidyougethere?"), 400

#Insert new question into question bank
@questions.route('/new_question', methods=['POST'])
def insert_new_question():
    cur = mysql.connection.cursor()
    
    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        pid = req['professorID'] #need this id to make sure the right questionID is retreived after the question is created
        title = req['title']
        topic = req['category']
        difficulty = req['difficulty']
        question = req['description']
        madeby = req['professorID']
        testcases = req['testCases']
        constraint = req['constraint']

        call = testcases[0]['functionCall']
        funcname = call.partition('(')[0]

        #question
        cur.execute("""INSERT INTO questions(id, title, topics, question, difficulty, madeby)
                                       VALUES(null,%s, %s, %s, %s, %s)""",(title, topic, question, difficulty, madeby))
        mysql.connection.commit()
        cur.execute("""SELECT MAX(id) as id 
                       FROM questions 
                       WHERE madeby = %s""",(pid,))
        qid = cur.fetchall()[0]['id']

        #namecriteria
        cur.execute("""INSERT INTO gradableitems(id, qid, criteriatable)
                       VALUES (null, %s, %s)""",(qid, "namecriteria"))
        mysql.connection.commit()
        cur.execute("""SELECT MAX(id) as id
                       FROM gradableitems 
                       WHERE qid = %s""",(qid,))
        gid = cur.fetchall()[0]['id']
        cur.execute("""INSERT INTO namecriteria(id, gid, fname)
                       VALUES(null, %s, %s)""",(gid, funcname)) 
        mysql.connection.commit()

        #constraint
        if constraint != "None" and constraint != "none":
            cur.execute("""INSERT INTO gradableitems(id, qid, criteriatable)
                        VALUES (null, %s, %s)""",(qid, "constraints"))
            mysql.connection.commit()
            cur.execute("""SELECT MAX(id) as id
                        FROM gradableitems
                        WHERE qid = %s""",(qid,))
            gid = cur.fetchall()[0]['id']
            cur.execute("""INSERT INTO constraints(id, gid, ctype)
                        VALUES(null, %s, %s)""",(gid, constraint)) 
            mysql.connection.commit()

        #testcases 
        for case in testcases:
            caseI = case['functionCall']
            caseO = case['expectedOutput']
            output_type = case['type']
            cur.execute("""INSERT INTO gradableitems(id, qid, criteriatable)
                           VALUES (null, %s, %s)""",(qid, "testcase"))
            mysql.connection.commit()
            cur.execute("""SELECT MAX(id) as id
                           FROM gradableitems 
                           WHERE qid = %s""",(qid,))
            gid = cur.fetchall()[0]['id']
            cur.execute("""INSERT INTO testcase(id, gid, input, output, outputtype)
                           VALUES(null, %s, %s, %s, %s)""",(gid, caseI, caseO, output_type))
            mysql.connection.commit()
        
        return jsonify(questionID = qid), 201
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

# Retrieve question info given question id
@questions.route('/retrieve_question', methods=['POST'])
def retrieve_question_details():
    cur = mysql.connection.cursor()
    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        qid = req['questionID']
        rows = cur.execute("""SELECT * 
                              FROM questions 
                              WHERE id = %s""",(qid,))
        if rows > 0:
            res = cur.fetchall()[0]
            return jsonify(res), 200
        else:
            return jsonify(error="INVALID QUESTION ID"), 400
    else:
        return jsonify(error="RECEIVED DATA ISN'T IN JSON FORMAT"), 400

# Retrieve test cases for given questionID
@questions.route('/test_cases', methods=['GET'])
def retrieve_test_cases():
    cur = mysql.connection.cursor()

    qid = request.args.get("questionID")
    rows = cur.execute("""SELECT id
                          FROM gradableitems
                          WHERE qid = %s AND criteriatable = %s""",(qid,'testcase'))

    if rows > 0:
        cases = list()
        rows = cur.fetchall()
        for row in rows:
            gid = row['id']
            rows = cur.execute("""SELECT input AS functionCall, output AS expectedOutput, outputtype AS type 
                                  FROM testcase 
                                  WHERE gid = %s""",(gid,))
            cases.append(cur.fetchall()[0])
        return jsonify(cases), 200
    else:
        return jsonify(error="INVALID QUESTION ID"), 400
    


@questions.route('/exam_questions', methods=['POST'])
def retrieve_exam_questions():
    cur = mysql.connection.cursor()
    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        eid = req['examID']
        rows = cur.execute("""SELECT name, open
                              FROM exams
                              WHERE id = %s""",(eid,))
        result = cur.fetchall()[0]
        examname = result['name']
        examstatus = result['open']
        rows = cur.execute("""SELECT eq.id as eqid, q.id AS qid, eq.points as points, q.title AS title, q.question AS question, q.difficulty AS difficulty 
                              FROM questions AS q, examquestions AS eq
                              WHERE  eq.eid = %s && eq.qid = q.id""",(eid,))
        
        if rows > 0:
            result = cur.fetchall()
            return jsonify(name=examname,status=examstatus,questions=result), 200
        else:
            return jsonify(error="NO QUESTIONS FOUND FOR THIS EXAM"), 400
    else:
        return jsonify(error="RECEIVED DATA ISN'T IN JSON FORMAT"), 400


