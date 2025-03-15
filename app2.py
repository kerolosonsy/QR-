from flask import Flask, render_template, request, jsonify
import pyodbc
import qrcode
import os

app = Flask(__name__)

# إعداد الاتصال بقاعدة البيانات
server = 'DESKTOP-7L2TS2S\\SQLEXPRESS'
database = 'Church'
driver = '{ODBC Driver 17 for SQL Server}'
conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

# إنشاء مجلد لحفظ QR Codes
QR_FOLDER = "static/qrcodes"
os.makedirs(QR_FOLDER, exist_ok=True)

def get_names():
    """إحضار الأسماء وإنشاء QR Code لكل شخص"""
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM dbo.QR")
    data = cursor.fetchall()
    conn.close()

    # إنشاء QR Code لكل شخص
    for person_id, name in data:
        qr = qrcode.make(str(person_id))
        qr.save(os.path.join(QR_FOLDER, f"{person_id}.png"))
    
    return data

def mark_attendance(attendance_list):
    """تحديث الحضور في قاعدة البيانات"""
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    for person_id in attendance_list:
        cursor.execute("INSERT INTO dbo.Attendance (person_id, date) VALUES (?, GETDATE())", person_id)
    
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    names = get_names()
    
    if request.method == "POST":
        selected_ids = request.form.getlist("attendance")
        mark_attendance(selected_ids)
    
    return render_template("attendance.html", names=names)

@app.route("/scan_qr", methods=["GET"])
def scan_qr():
    """تحليل QR Code الممسوح وإرجاع بيانات المستخدم"""
    qr_data = request.args.get("data")
    if not qr_data:
        return jsonify({"status": "error", "message": "لم يتم العثور على بيانات QR"}), 400

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM dbo.QR WHERE id = ?", qr_data)
    person = cursor.fetchone()
    conn.close()

    if person:
        return jsonify({"status": "success", "id": qr_data, "name": person[0]})
    else:
        return jsonify({"status": "error", "message": "المستخدم غير موجود"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
