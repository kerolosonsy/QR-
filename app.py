from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import pyodbc
import qrcode
import os
import io
import math
import datetime

app = Flask(__name__)

# Database Connection
server = 'Re3aya-dev.my-alphatech.com\MSSQLSERVER2019'
username = 'Alph_Maria'
password = 'tp8895Ma#'
database = 'alphatec_Attendance'
driver = '{ODBC Driver 17 for SQL Server}'
conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'

# Folder for storing QR codes
QR_FOLDER = "static/qrcodes"
os.makedirs(QR_FOLDER, exist_ok=True)

# Function to Generate QR Code
def generate_qr(data):
    qr = qrcode.make(data)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    return buffered.getvalue()

@app.route("/")
def home():
    return render_template("home.html")

# Route: Home Page (Form + Admin Table)
@app.route("/index", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        id_number = request.form["id"]

        if not id_number.isdigit() or len(id_number) != 4:
            return "❌ Please enter a valid 4-digit number!"

        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            # Check if ID exists
            cursor.execute("SELECT COUNT(*) FROM dbo.QR WHERE id = ?", (id_number,))
            if cursor.fetchone()[0] > 0:
                return "❌ ID already exists!"

            qr_binary = generate_qr(id_number)
            cursor.execute("INSERT INTO dbo.QR (name, id, qr) VALUES (?, ?, ?)", 
                           (name, int(id_number), pyodbc.Binary(qr_binary)))
            conn.commit()
            conn.close()

            return redirect(url_for("index"))

        except Exception as e:
            return f"❌ Error: {e}"

    # Pagination
    page = request.args.get("page", 1, type=int)
    limit = 10
    offset = (page - 1) * limit

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("SELECT name, id FROM dbo.QR ORDER BY id OFFSET ? ROWS FETCH NEXT ? ROWS ONLY", (offset, limit))
        records = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM dbo.QR")
        total_records = cursor.fetchone()[0]

        conn.close()

        total_pages = math.ceil(total_records / limit)
        return render_template("index.html", records=records, page=page, total_pages=total_pages)

    except Exception as e:
        return f"❌ Error: {e}"

# Route: Mark Attendance
@app.route('/mark_attendance', methods=["POST"])
def mark_attendance():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    selected_ids = request.form.getlist("attendance")

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Delete previous records for today
        cursor.execute("DELETE FROM Attendance WHERE date = ?", (today,))

        # Insert attendance for all persons
        cursor.execute("SELECT id, name FROM QR")
        all_persons = cursor.fetchall()

        for person_id, name in all_persons:
            status = 1 if str(person_id) in selected_ids else 0
            cursor.execute(
                "INSERT INTO Attendance (person_id, name, date, status) VALUES (?, ?, ?, ?)",
                (person_id, name, today, status)
            )

        conn.commit()
        conn.close()
        return redirect(url_for('attendance'))

    except Exception as e:
        return f"❌ Error: {e}"

# Route: Attendance Page
@app.route('/attendance', methods=["GET", "POST"])
def attendance():
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Fetch attendance data
        cursor.execute("""
            SELECT Q.id, Q.name, COALESCE(A.status, 0) AS status
            FROM QR Q
            LEFT JOIN Attendance A 
            ON Q.id = A.person_id AND A.date = ?
        """, (today,))

        records = cursor.fetchall()
        conn.close()

        return render_template("attendance.html", records=records, today=today)

    except Exception as e:
        return f"❌ Error: {e}"

# Route: View QR Code
@app.route("/view_qr/<id_number>")
def view_qr(id_number):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("SELECT qr FROM dbo.QR WHERE id = ?", (id_number,))
        row = cursor.fetchone()

        if row:
            return send_file(io.BytesIO(row[0]), mimetype="image/png")
        return "❌ No QR code found for this ID!"

    except Exception as e:
        return f"❌ Error: {e}"



@app.route("/delete/<id_number>")
def delete_record(id_number):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Step 1: Delete attendance records related to this person
        cursor.execute("DELETE FROM dbo.Attendance WHERE person_id = ?", (id_number,))
        
        # Step 2: Delete the person from the QR table
        cursor.execute("DELETE FROM dbo.QR WHERE id = ?", (id_number,))

        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    except pyodbc.Error as db_err:
        return f"❌ Database Error: {db_err}"

    except Exception as e:
        return f"❌ Unexpected Error: {e}"


# Route: Edit Record
@app.route("/edit/<id_number>", methods=["POST"])
def edit_record(id_number):
    new_name = request.form["name"]
    new_id = request.form["new_id"]

    if not new_id.isdigit() or len(new_id) != 4:
        return "❌ Please enter a valid 4-digit number!"

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Check if new ID already exists
        cursor.execute("SELECT COUNT(*) FROM dbo.QR WHERE id = ?", (new_id,))
        if cursor.fetchone()[0] > 0 and new_id != id_number:
            return "❌ New ID already exists!"

        qr_binary = generate_qr(new_id)
        cursor.execute("UPDATE dbo.QR SET name = ?, id = ?, qr = ? WHERE id = ?", 
                       (new_name, int(new_id), pyodbc.Binary(qr_binary), id_number))
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    except Exception as e:
        return f"❌ Error: {e}"

# Route: Scan QR Code
@app.route("/scan_qr", methods=["GET"])
def scan_qr():
    qr_data = request.args.get("data")
    if not qr_data:
        return jsonify({"status": "error", "message": "لم يتم العثور على بيانات QR"}), 400

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM dbo.QR WHERE id = ?", qr_data)
        person = cursor.fetchone()
        conn.close()

        if person:
            return jsonify({"status": "success", "id": qr_data, "name": person[0]})
        return jsonify({"status": "error", "message": "المستخدم غير موجود"}), 404

    except Exception as e:
        return f"❌ Error: {e}"


@app.route('/reset_attendance', methods=['POST'])
def reset_attendance():
    try:
        # Connect to SQL Server
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Set all attendance values to 0 for today
        cursor.execute("UPDATE Attendance SET status = 0 WHERE date = CAST(GETDATE() AS DATE)")
        conn.commit()
        conn.close()

        # return jsonify({"message": "✅ تم إعادة ضبط الحضور بنجاح!"}), 200

    except pyodbc.Error as db_err:
        return jsonify({"error": f"❌ Database Error: {db_err}"}), 500
    except Exception as e:
        return jsonify({"error": f"❌ Unexpected Error: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
