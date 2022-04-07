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
            cur.execute("""INSERT INTO results(id, eaid, score) 
                           VALUES (null, %s, %s)""",(eaid, escore))
            mysql.connection.commit()
            cur.execute("""SELECT MAX(id) AS id 
                           FROM results WHERE eaid = %s
                           ORDER BY id DESC""", (eaid,))
            rid = cur.fetchall()[0]['id']
            questions = attempt['questionresults']
            for question in questions:
                eqid = question['examquestionID']
                qscore = question['questionscore']
                gradables = question['gradables']
                cur.execute("""INSERT INTO questionresults(id, rid, eqid, score) 
                               VALUES (null, %s, %s)""",(rid, eqid, qscore))
                mysql.connection.commit()
                cur.execute("""SELECT MAX(id) as id
                               FROM questionresults
                               WHERE rid = %s AND eqid = %s""", (rid, eqid))
                qrid = cur.fetchall()[0]['id']
                for g in gradables:    
                    cur.execute("""INSERT INTO gradableresults(id, qrid, egid, score, expected, received) 
                                VALUES (null, %s, %s, %s, %s, %s)""",(qrid, eqid, g['score'], g['expected'], g['received']))
                    mysql.connection.commit()
            resultIDs.append({'examattemptID':eaid, 'resultID':rid})
            cur.execute("""UPDATE examattempts 
                           SET graded=1 
                           WHERE id = %s""", (eaid,))
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
        rows = cur.execute("""SELECT id, name, points 
                              FROM exams 
                              WHERE id = %s""",(eid,))
        if rows == 0:
            return jsonify(error="EXAM ID NOT VALID")
        exam = cur.fetchall()[0]
        examname = exam['name']
        maxexamscore = exam['points']
        
        if role == 'Student':
            sid = req['studentID']
            rows = cur.execute("""SELECT id AS eaid, sid 
                                  FROM examattempts 
                                  WHERE eid={eid} AND sid={sid} ORDER BY id DESC""",(eid, sid))
        else: 
            rows = cur.execute("""SELECT id AS eaid, sid 
                                  FROM examattempts 
                                  WHERE eid = %s 
                                  ORDER BY id DESC""",(eid,))

        if rows > 0:
            examattempts = cur.fetchall()
            rows = cur.execute("""SELECT id AS eqid, qid, points 
                                  FROM examquestions 
                                  WHERE eid = %s""",(eid,))
            examquestions= cur.fetchall()
            attempts = list()
            for attempt in examattempts:
                eaid = attempt['eaid']
                sid = attempt['sid']
                cur.execute("""SELECT firstname, lastname 
                               FROM students 
                               WHERE id = %s""",(sid,))
                student = cur.fetchall()[0]
                fname = student['firstname']
                lname = student['lastname']
                cur.execute("""SELECT id, score
                               FROM results
                               WHERE eaid = %s
                               ORDER BY id DESC""",(eaid,))
                result = cur.fetchall()[0]
                rid = result['id']
                attemptscore = result['score']
                questions = list()
                for eq in examquestions:
                    maxqpoints = eq['points']
                    qid = eq['qid']
                    eqid = eq['eqid']
                    cur.execute("""SELECT title, question 
                                   FROM questions 
                                   WHERE id = %s""", (qid,))
                    q = cur.fetchall()[0]
                    qtitle = q['title']
                    qq = q['question']
                    cur.execute("""SELECT answer 
                                   FROM examattemptanswers 
                                   WHERE eaid = %s AND eqid = %s""",(eaid, eqid))
                    ans = cur.fetchall()[0]['answer']
                    cur.execute("""SELECT id AS qrid, score 
                                   FROM questionresults 
                                   WHERE rid = %s AND eqid = %s""",(rid, eqid))
                    qresult = cur.fetchall()[0]
                    qscore = qresult['score']
                    qrid = qresult['qrid']
                    cur.execute("""SELECT id AS grid, qrid, egid, score, expected, received
                                   FROM gradableresults
                                   WHERE qrid = %s""", (qrid,))
                    gresults = cur.fetchall()
                    gradables = list()
                    pleft = 1.00
                    for gr in gresults:
                        cur.execute("""SELECT points, gid
                                       FROM examgradableitems
                                       WHERE id = %s""", (gr['egid'],))
                        eg = cur.fetchall()
                        maxgpoints = eg['points']
                        maxp = round(maxgpoints/maxqpoints, 2)
                        if pleft < 0.00:
                            maxp+=pleft
                        pleft-=maxp
                        gid = ['gid']
                        cur.execute("""SELECT criteriatable AS cr
                                       FROM gradableitems
                                       WHERE id = %s""", (gid,))
                        cr = cur.fetchall()['cr']
                        if cr == "namecriteria":
                            cr = "Name"
                        elif cr == "testcase":
                            cr = "Testcase"
                        else:
                            cr = "Constraint"
                        gradables.append({'egid':gr['egid'], 'maxgrade':{'points':maxgpoints, 'percentage':maxp}, 'type':cr, 'score':gr['score'], 'expected':gr['expected'], 'received':gr['received']})
                    questions.append({'examquestionID':eqid, 'title':qtitle, 'questions':qq, 'qscore':qscore, 'maxpoints':maxqpoints, 'response': ans.decode("utf-8")})
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