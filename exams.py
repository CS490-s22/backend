from flask import Blueprint, jsonify, request, current_app as app
from flask_cors import cross_origin
from database import mysql
import logging

exams = Blueprint("exams",__name__)

#Create new exam
@exams.route('/new_exam',methods=['POST'])
def create_new_exam():
    cur = mysql.connection.cursor()
    if request.method != 'POST':
        return jsonify(error="REQUIRES POST REQUEST"), 400

    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        name = req['name']
        details = req['description']
        madeby = req['professorID']
        questions = req['questions']

        totalpoints = 0
        for q in questions:
            totalpoints += int(q['points'])

        rows = cur.execute("INSERT INTO exams(id, name, details, madeby, points) VALUES(null,\"{}\",\"{}\",\"{}\",{})".format(name, details, madeby, totalpoints))
        mysql.connection.commit()
        logging.warn("ROWS INSERTED INTO Exams: %d", rows)

        cur.execute("SELECT MAX(id) AS id FROM exams")
        eid = cur.fetchall()[0]['id']
        for q in questions:
            qid = q['questionID']
            points = q['points']
            cur.execute("INSERT INTO examquestions(id, eid, qid, points) VALUES(null, {}, {}, {})".format(eid, qid, points))
            mysql.connection.commit()

        return jsonify(examID=eid), 201
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@exams.route('/exams', methods=['POST'])
def retreive_exams():
    cur = mysql.connection.cursor()
    content_type = request.headers.get("Content-Type")
    if content_type == "application/json":
        req = request.json
        role = req['role']
        if role == "Student":
            rows = cur.execute("SELECT * FROM exams WHERE open = 1 ORDER BY id DESC")
        else:
            rows = cur.execute("SELECT exams.*, COUNT(examattempts.eid) AS attempts FROM exams LEFT JOIN examattempts ON exams.id = examattempts.eid GROUP BY exams.id;")
        if rows > 0:
            result = cur.fetchall()
            return jsonify(result)
        else:
            return jsonify(error="NO EXAMS")
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@exams.route('/exam_status', methods=['POST'])
def check_exam_status():
    cur = mysql.connection.cursor()

    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        examID = req['examID']
        rows = cur.execute('SELECT open FROM exams WHERE id = {}'.format(examID))

        if rows > 0:
            result = cur.fetchall()[0]['open']

            return jsonify(open=bool(result)), 200
        else:
            return jsonify(error="NO SUCH EXAM ID FOUND"), 400
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@exams.route('/change_exam_status', methods=['POST'])
@cross_origin(allow_headers=['Content-Type'])
def change_exam_status():
    logging.getLogger('flask_cors').level = logging.DEBUG
    cur = mysql.connection.cursor()

    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        examID = req['examID']
        status = req['status']
        try:
            cur.execute('UPDATE exams SET open = {} WHERE id = {}'.format(status, examID))
            mysql.connection.commit()
            return jsonify(resonse="STATUS CHANGED!"), 200
        except:
            return jsonify(error="QUERY ERROR"), 400
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@exams.route('/submit_exam_attempt', methods=['POST'])
def submit_exam_attempt():
    cur = mysql.connection.cursor()

    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        eid = req['examID']
        sid = req['studentID']
        pid = req['professorID']
        answers = req['answers']
        cur.execute(f'INSERT INTO examattempts(id, sid, pid, eid) VALUES (null, {sid}, {pid}, {eid})')
        mysql.connection.commit()
        rows = cur.execute(f'SELECT id FROM examattempts WHERE sid={sid} AND pid={pid} AND eid={eid} ORDER BY id DESC LIMIT 1')
        if rows > 0:
            eaid = cur.fetchall()[0]['id']
            for answer in answers:
                eqid = answer['eqid']
                response = answer['answer']
                cur.execute("""INSERT INTO examattemptanswers(id, eqid, eaid, answer) VALUES (null, %s, %s, %s)""", (eqid, eaid, response))
                mysql.connection.commit()
            return jsonify(examattemptID=eaid), 200
        else:
            return jsonify(error="EXAM ATTEMPT FAILED TO SUBMIT, CHECK PROVIED CREDENTIAL"), 400
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@exams.route('/exam_attempts', methods=['POST'])
def retrieve_exam_attempt():
    cur = mysql.connection.cursor()

    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        eid = req['examID']
        rows = cur.execute(f'SELECT * FROM exams WHERE id={eid}')
        if rows == 0:
            return jsonify(error="EXAM ID NOT VALID")
        rows = cur.execute(f'SELECT id AS eaid, sid FROM examattempts WHERE eid={eid}')
        if rows > 0:
            examattempts = cur.fetchall()
            rows = cur.execute(f'SELECT id AS eqid, qid FROM examquestions WHERE eid={eid}')
            examquestions= cur.fetchall()
            attempts = list()
            for attempt in examattempts:
                eaid = attempt['eaid']
                sid = attempt['sid']
                questions = list()
                for eq in examquestions:
                    qid = eq['qid']
                    eqid = eq['eqid']
                    print(eaid, eqid, "TESTSTESTSETSETSE")
                    rows = cur.execute(f'SELECT answer FROM examattemptanswers WHERE eaid = {eaid} AND eqid={eqid}')
                    ans = cur.fetchall()[0]['answer']
                    rows = cur.execute(f'SELECT input, output, outputtype FROM testcases WHERE qid={qid}')
                    testcases = cur.fetchall()
                    cases = list()
                    for case in testcases:
                        cases.append({'functionCall': case['input'], 'expectedOutput':case['output'], 'type': case['outputtype']})
                    questions.append({'examquestionID':eqid, 'testcases':cases, 'response': ans.decode("utf-8")})
                attempts.append({"studentID": sid, "examattemptID": eaid, "questions":questions})
            return jsonify(attempts)
        else:
            return jsonify(error="NO SUBMISSIONS FOR THIS EXAM")
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400
