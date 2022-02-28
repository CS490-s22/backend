from flask import Blueprint, jsonify, request, current_app as app
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
            totalpoints += q['points']

        rows = cur.execute("INSERT INTO exams(id, name, details, madeby, points) VALUES(null,\"{}\",\"{}\",\"{}\",{})".format(name, details, madeby, totalpoints))
        mysql.connection.commit()
        logging.warn("ROWS INSERTED INTO Exams: %d", rows)

        cur.execute("SELECT MAX(id) AS id FROM exams")
        eid = cur.fetchall()[0]['id']
        for q in questions:
            qid = q['questionID']
            points = q['points']
            cur.execute("INSERT INTO examsquestions(id, eid, qid, points) VALUES(null, {}, {}, {})".format(eid, qid, points))
            mysql.connection.commit()

        return jsonify(examID=eid), 201
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400
