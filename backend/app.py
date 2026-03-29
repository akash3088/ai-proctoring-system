from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'flagged_videos')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

flagged_events = []
students = {}  

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/demo_exam')
def demo_exam():
    return render_template('demo_exam.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    try:
        username = request.form.get('username', 'Unknown')
        if not request.files:
            return jsonify({'error': 'No video provided'}), 400
        file = list(request.files.values())[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{username}_{timestamp}.mp4"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        flagged_events.append({'username': username, 'filename': filename, 'time': timestamp})
        return jsonify({'message': 'Video uploaded successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/warning', methods=['POST'])
def warning():
    data = request.get_json()
    username = data.get('username')
    reason = data.get('reason', 'Suspicious activity')
    if username not in students:
        students[username] = {'warnings': 0, 'exam_failures': 0, 'blocked_until': None}
    student = students[username]
    now = datetime.now()
    if student['blocked_until'] and now < student['blocked_until']:
        return jsonify({'message': f'Student {username} is blocked until {student["blocked_until"]}'})
    student['warnings'] += 1
    flagged_events.append({'username': username, 'reason': reason, 'time': now.strftime('%Y-%m-%d %H:%M:%S')})
    alert_msg = f"Warning {student['warnings']} for {username}: {reason}"
    if student['warnings'] >= 3:
        student['exam_failures'] += 1
        student['warnings'] = 0
        if student['exam_failures'] >= 3:
            student['blocked_until'] = now + timedelta(weeks=1)
            alert_msg += f" | Student blocked for 1 week due to repeated suspicious exams"
        else:
            alert_msg += f" | Exam closed for {username}"
    print(alert_msg)
    return jsonify({'message': alert_msg})

@app.route('/events', methods=['GET'])
def get_events():
    return jsonify(flagged_events)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
