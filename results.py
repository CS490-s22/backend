from flask import Blueprint, jsonify, request, current_app as app
from database import mysql

results = Blueprint("results",__name__)

@results.route('/score_attempts', methods=['POST'])
def score_exams_attempts():
    cur = mysql.connection.cursor()

    content_type = request.headers.get("Content-Type")
    resultIDs = list()
    if content_type == "application/json":
        attempts = request.json

        for attempt in attempts:
            eaid = attempt['examattemptID']
            escore = attempt['score']
            cur.execute(f'INSERT INTO results(id, eaid, score) VALUES (null, {eaid}, {escore})')
            mysql.connection.commit()
            cur.execute(f'SELECT MAX(id) AS id FROM results WHERE eaid={eaid} ORDER BY id DESC')
            rid = cur.fetchall()[0]['id']
            questions = attempt['questionresults']
            for question in questions:
                eqid = question['examquestionID']
                qscore = question['questionscore']
                cur.execute(f'INSERT INTO questionresults(id, rid, eqid, score) VALUES (null, {rid}, {eqid}, {qscore})')
                mysql.connection.commit()
            resultIDs.append({'examattemptID':eaid, 'resultID':rid})
            cur.execute(f'UPDATE examattempts SET graded=1 WHERE id={eaid}')
            mysql.connection.commit()
        return jsonify(resultIDs), 200
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@results.route('/view_results', methods=['POST'])
def retrieve_exam_results():
    cur = mysql.connection.cursor()
    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        eid = req['examID']
        role = req['role']
        rows = cur.execute(f'SELECT id, name, points FROM exams WHERE id={eid}')
        if rows == 0:
            return jsonify(error="EXAM ID NOT VALID")
        exam = cur.fetchall()[0]
        examname = exam['name']
        maxexamscore = exam['points']
        
        if role == 'Student':
            sid = req['studentID']
            query = f'SELECT id AS eaid, sid FROM examattempts WHERE eid={eid} AND sid={sid} ORDER BY id DESC'
        else: 
            query = f'SELECT id AS eaid, sid FROM examattempts WHERE eid={eid} ORDER BY id DESC'
        rows = cur.execute(query)

        if rows > 0:
            examattempts = cur.fetchall()
            rows = cur.execute(f'SELECT id AS eqid, qid, points FROM examquestions WHERE eid={eid}')
            examquestions= cur.fetchall()
            attempts = list()
            for attempt in examattempts:
                eaid = attempt['eaid']
                sid = attempt['sid']
                cur.execute(f'SELECT firstname, lastname FROM students WHERE id={sid}')
                student = cur.fetchall()[0]
                fname = student['firstname']
                lname = student['lastname']
                cur.execute(f'SELECT id, score FROM results WHERE eaid={eaid} ORDER BY id DESC')
                result = cur.fetchall()[0]
                rid = result['id']
                attemptscore = result['score']
                questions = list()
                for eq in examquestions:
                    maxpoints = eq['points']
                    qid = eq['qid']
                    eqid = eq['eqid']
                    cur.execute(f'SELECT title, question FROM questions WHERE id={qid}')
                    q = cur.fetchall()[0]
                    qtitle = q['title']
                    qq = q['question']
                    cur.execute(f'SELECT answer FROM examattemptanswers WHERE eaid = {eaid} AND eqid={eqid}')
                    ans = cur.fetchall()[0]['answer']
                    cur.execute(f'SELECT id AS qrid, score FROM questionresults WHERE rid={rid} AND eqid={eqid}')
                    qresult = cur.fetchall()[0]
                    qscore = qresult['score']
                    qrid = qresult['qrid']
                    questions.append({'examquestionID':eqid, 'title':qtitle, 'questions':qq, 'qscore':qscore, 'maxpoints':maxpoints, 'response': ans.decode("utf-8")})
                attempts.append({"studentID": sid, 'fname':fname, 'lname':lname, "examattemptID": eaid, "resultID":rid, 'score':attemptscore, "questions":questions})
            return jsonify({'examname':examname,'maxexampoints':maxexamscore,'examattempts':attempts}), 200
        else:
            return jsonify(error="NO SUBMISSIONS FOR THIS EXAM"), 400
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@results.route('/view_result', methods=['POST'])
def retrieve_exam_result():
    cur = mysql.connection.cursor()
    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        eid = req['examID']
        eaid = req['examattemptID']
        rid = req['resultID']
        rows = cur.execute(f'SELECT id, name, points FROM exams WHERE id={eid}')
        if rows == 0:
            return jsonify(error="EXAM ID NOT VALID")
        exam = cur.fetchall()[0]
        examname = exam['name']
        maxexamscore = exam['points']
        rows = cur.execute(f'SELECT sid FROM examattempts WHERE id={eaid}')
        if rows > 0:
            examattempt = cur.fetchall()[0]
            rows = cur.execute(f'SELECT id AS eqid, qid, points FROM examquestions WHERE eid={eid}')
            examquestions= cur.fetchall()
            sid = examattempt['sid']
            cur.execute(f'SELECT firstname, lastname FROM students WHERE id={sid}')
            student = cur.fetchall()[0]
            fname = student['firstname']
            lname = student['lastname']
            cur.execute(f'SELECT score FROM results WHERE id={rid}')
            result = cur.fetchall()[0]
            attemptscore = result['score']
            questions = list()
            for eq in examquestions:
                maxpoints = eq['points']
                qid = eq['qid']
                eqid = eq['eqid']
                cur.execute(f'SELECT title, question FROM questions WHERE id={qid}')
                q = cur.fetchall()[0]
                qtitle = q['title']
                qq = q['question']
                cur.execute(f'SELECT answer FROM examattemptanswers WHERE eaid = {eaid} AND eqid={eqid}')
                ans = cur.fetchall()[0]['answer']
                cur.execute(f'SELECT score, remark FROM questionresults WHERE rid={rid} AND eqid={eqid}')
                qresult = cur.fetchall()[0]
                qscore = qresult['score']
                comment = qresult['remark']
                questions.append({'examquestionID':eqid, 'title':qtitle, 'question':qq, 'qscore':qscore, 'maxpoints':maxpoints, 'response': ans.decode("utf-8"), 'comments':comment})
            attempt = {"studentID": sid, 'fname':fname, 'lname':lname, "examattemptID": eaid, "resultID":rid, 'score':attemptscore, "questions":questions}
            return jsonify({'examname':examname,'maxexampoints':maxexamscore,'examattempt':attempt}), 200
        else:
            return jsonify(error="NO SUBMISSIONS FOR THIS EXAM"), 400
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@results.route('/edit_result', methods=['POST'])
def edit_result():
    cur = mysql.connection.cursor()
    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        rid = req['resultID']
        qs = req['questions']
        examscore = 0
        for q in qs:
            eqid = q['examquestionID']
            comment = q['comment']
            score = q['score']
            examscore += score
            cur.execute("""UPDATE questionresults SET score=%s, remark=%s WHERE rid=%s AND eqid=%s""", (score, comment, rid, eqid))
            mysql.connection.commit()
        cur.execute(f'UPDATE results SET score={examscore} WHERE id ={rid}')
        mysql.connection.commit()
        return jsonify(resultID=rid), 200
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400