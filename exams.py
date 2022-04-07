from flask import Blueprint, jsonify, request, current_app as app
from flask_cors import cross_origin
from database import mysql
import logging, math

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

        cur.execute("""INSERT INTO exams(id, name, details, madeby, points) 
                       VALUES(null, %s, %s, %s, %s)""",(name, details, madeby, totalpoints))
        mysql.connection.commit()
        cur.execute("""SELECT MAX(id) AS id 
                       FROM exams
                       WHERE madeby = %s""",(madeby,))
        eid = cur.fetchall()[0]['id']

        for q in questions:
            qid = q['questionID']
            points = q['points']
            cur.execute("""INSERT INTO examquestions(id, eid, qid, points)
                           VALUES(null, {}, {}, {})""",(eid, qid, points))
            mysql.connection.commit()
            cur.execute("""SELECT MAX(id) AS id 
                           FROM examquestions
                           WHERE eid = %s AND qid = %s""", (eid, qid))
            eqid = cur.fetchall()[0]['id']
            cur.execute("""SELECT id, criteriatable AS ct
                           FROM gradabaleitems
                           WHERE qid = %s""",(qid,))
            rows = cur.fetchall()
            ntcc = 0
            for gradeable in rows:
                gid = gradeable['id']
                if gradeable['ct'] == 'namecriteria':
                    gmaxgrade = 0.1 * points
                    ntcc+=1
                elif gradeable['ct'] == 'constraints':
                    gmaxgrade = 0.1 * points
                    ntcc+=1
                else:
                    gmaxgrade =  round(((1.0 - (0.1 * ntcc)) * points) / (len(rows)-ntcc),2)
                    if ntcc != 0:
                        leftover = 1.0 - round(gmaxgrade * 3, 2)
                        gmaxgrade += leftover
                        ntcc = 0
                
                cur.execute("""INSERT INTO examgradableitems(id, eqid, gid, points)
                               VALUES(null, %s, %s, %s)""",(eqid, gid, gmaxgrade))
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
            stype = req['statustype']
            if stype == "released":
                sid = req['studentID']
                rows = cur.execute("""SELECT DISTINCT(e.id), e.name AS name, e.details AS details, e.madeby AS madeby, e.points AS points, e.open AS open, e.released AS released 
                                      FROM exams AS e, examattempts
                                      WHERE e.id=examattempts.eid AND examattempts.sid = %s AND e.released = 1 AND examattempts.graded = 1""",(sid,))
            else:
                rows = cur.execute("""SELECT * 
                                      FROM exams 
                                      WHERE open = 1 
                                      ORDER BY id DESC""")
        else:
            rows = cur.execute("""SELECT exams.*, COUNT(examattempts.eid) AS attempts 
                                  FROM exams LEFT JOIN examattempts 
                                  ON exams.id = examattempts.eid 
                                  GROUP BY exams.id;""")
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
        rows = cur.execute("""SELECT open 
                              FROM exams 
                              WHERE id = %s""",(examID,))

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
            cur.execute("""UPDATE exams 
                           SET open = %s 
                           WHERE id = %s""",(status, examID))
            mysql.connection.commit()
            return jsonify(resonse="STATUS CHANGED!"), 200
        except:
            return jsonify(error="QUERY ERROR"), 400
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@exams.route('/change_release_status', methods=['POST'])
@cross_origin(allow_headers=['Content-Type'])
def change_release_status():
    logging.getLogger('flask_cors').level = logging.DEBUG
    cur = mysql.connection.cursor()

    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        examID = req['examID']
        released = req['status']
        try:
            cur.execute("""UPDATE exams 
                           SET released = %s 
                           WHERE id = %s""",(released, examID))
            mysql.connection.commit()
            return jsonify(resonse=f"RELEASE STATUS FOR EXAM {examID}: {released}"), 200
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
        cur.execute("""INSERT INTO examattempts(id, sid, pid, eid) 
                       VALUES (null, %s, %s, %s)""", (sid, pid, eid))
        mysql.connection.commit()
        rows = cur.execute("""SELECT id 
                              FROM examattempts 
                              WHERE sid=%s AND pid=%s AND eid=%s 
                              ORDER BY id DESC LIMIT 1""",(sid, pid, eid))
        if rows > 0:
            eaid = cur.fetchall()[0]['id']
            for answer in answers:
                eqid = answer['eqid']
                response = answer['answer']
                cur.execute("""INSERT INTO examattemptanswers(id, eqid, eaid, answer) 
                               VALUES (null, %s, %s, %s)""", (eqid, eaid, response))
                mysql.connection.commit()
            return jsonify(examattemptID=eaid), 200
        else:
            return jsonify(error="EXAM ATTEMPT FAILED TO SUBMIT, CHECK PROVIED CREDENTIAL"), 400
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

#-----------
@exams.route('/exam_attempts', methods=['POST'])
def retrieve_exam_attempts_for_grading():
    cur = mysql.connection.cursor()

    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        eid = req['examID']
        rows = cur.execute("""SELECT * 
                              FROM exams 
                              WHERE id=%s""",(eid,))
        if rows == 0:
            return jsonify(error="EXAM ID NOT VALID"), 400
        rows = cur.execute("""SELECT id AS eaid, sid 
                              FROM examattempts 
                              WHERE eid = %s AND graded = 0""",(eid,))
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
                questions = list()
                for eq in examquestions:
                    points = eq['points']
                    qid = eq['qid']
                    eqid = eq['eqid']
                    rows = cur.execute("""SELECT answer 
                                          FROM examattemptanswers 
                                          WHERE eaid = %s AND eqid = %s""",(eaid, eqid))
                    ans = cur.fetchall()[0]['answer']
                    rows = cur.execute("""SELECT id, criteriatable AS ct
                                          FROM gradableitems
                                          WHERE qid = %s""",(qid,))
                    gradables = cur.fetchall()
                    glist = list()
                    for g in gradables:
                        ct = g['ct']
                        gid = g['id']
                        cur.execute("""SELECT fname 
                                           FROM examgradableitems
                                           WHERE eqid = %s AND gid = %s""",(eqid, gid))
                        maxgrade = cur.fetchall()[0]['points']
                        if ct == 'namecriteria':
                            gtype = 'name'
                            cur.execute("""SELECT fname 
                                           FROM namecriteria
                                           WHERE gid = %s""",(gid,))
                            name = cur.fetchall()[0]['fname']
                            glist.append({'gradableID': gid, 'type': gtype, 'name': name})
                        elif ct == 'constraints':
                            gtype = "constraint"
                            cur.execute("""SELECT ctype
                                           FROM constraints
                                           WHERE gid = %s""", (gid,))
                            ctype = cur.fetchall()[0]['ctype']
                            glist.append({'gradableID': gid, 'type': gtype, 'Constraint':ctype})
                        else:
                            gtype = "testcase"
                            rows = cur.execute("""SELECT input, output, outputtype 
                                                  FROM testcase 
                                                  WHERE gid = %s""",(gid,))
                            testcase = cur.fetchall()
                            glist.append({'gradableID': gid, 'maxgrade': maxgrade, 'type': gtype, 'case': {'functionCall': testcase['input'], 'expectedOutput': testcase['output'], 'type': testcase['outputtype']}})

                    questions.append({'examquestionID':eqid, 'points':points, 'gradables':glist, 'response': ans.decode("utf-8")})
                attempts.append({"studentID": sid, "examattemptID": eaid, "questions":questions})
            return jsonify(attempts), 200
        else:
            return jsonify(list()), 200
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400

@exams.route('/retrieve_exam_attempts', methods=['POST'])
def retrieve_exam_attempts():
    cur = mysql.connection.cursor()
    content_type = request.headers.get("Content-Type")
    if content_type == 'application/json':
        req = request.json
        eid = req['examID']
        rows = cur.execute("""SELECT * 
                              FROM exams 
                              WHERE id = %s""",(eid,))
        if rows == 0:
            return jsonify(error="INVALID EXAM ID")
        rows = cur.execute("""SELECT * 
                              FROM examattempts 
                              WHERE eid = %s""",(eid,))
        if rows > 0:
            res = cur.fetchall()
            return jsonify(res), 200
        else:
            return jsonify(error="NO ATTEMPTS WERE MADE FOR THIS EXAM"), 400
    else:
        return jsonify(error="RECEIVED DATA ISN'T IN JSON FORMAT"), 400