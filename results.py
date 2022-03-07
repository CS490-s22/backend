from flask import Blueprint, jsonify, request, current_app as app
from flask_cors import cross_origin
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
            cur.execute(f'INSERT INTO results(id, eaid, score) VALUES (null, {eaid}, {escore}')
            mysql.connection.commit()
            cur.execute(f'SELECT id FROM results WHERE eaid={eaid}')
            rid = cur.fetachall()[0]['id']
            questions = attempt['questionresults']
            for question in questions:
                eqid = question['examquestionID']
                qscore = questions['questionscore']
                cur.execute(f'INSERT INTO questionresults(id, rid, eqid, score) VALUES (null, {rid}, {eqid}, {qscore}')
            resultIDs.append({'examattemptID':eaid, 'resultID':rid})
        return jsonify(resultIDs), 200
    else:
        return jsonify(error="JSON FORMAT REQUIRED"), 400
