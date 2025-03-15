from flask import Flask, render_template, request, redirect, url_for, send_file
import pyodbc
import qrcode
import io
import math

app = Flask(__name__)

# Database connection string
server = 'DESKTOP-7L2TS2S\\SQLEXPRESS'
database = 'Church'
driver = '{ODBC Driver 17 for SQL Server}'
conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

# Function to generate QR code
def generate_qr(data):
    qr = qrcode.make(data)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    return buffered.getvalue()

# Route: Home Page (Form + Admin Table)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        id_number = request.form['id']

        if not id_number.isdigit() or len(id_number) != 4:
            return "❌ Please enter a valid 4-digit number!"

        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            qr_binary = generate_qr(id_number)  # Generate QR code as binary

            cursor.execute("INSERT INTO dbo.QR (name, id, qr) VALUES (?, ?, ?)", 
                           (name, int(id_number), pyodbc.Binary(qr_binary)))
            conn.commit()
            conn.close()

            return redirect(url_for('index'))  # Refresh the page to show updated data

        except Exception as e:
            return f"❌ Error: {e}"

    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = 5  # Number of records per page
    offset = (page - 1) * limit

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Fetch limited records for pagination
        cursor.execute("SELECT name, id FROM dbo.QR ORDER BY id OFFSET ? ROWS FETCH NEXT ? ROWS ONLY", (offset, limit))
        records = cursor.fetchall()

        # Get total number of records
        cursor.execute("SELECT COUNT(*) FROM dbo.QR")
        total_records = cursor.fetchone()[0]

        conn.close()

        total_pages = math.ceil(total_records / limit)  # Calculate total pages
        return render_template('index.html', records=records, page=page, total_pages=total_pages)

    except Exception as e:
        return f"❌ Error: {e}"

# Route: View QR Code
@app.route('/view_qr/<id_number>')
def view_qr(id_number):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("SELECT qr FROM dbo.QR WHERE id = ?", (id_number,))
        row = cursor.fetchone()

        if row:
            qr_binary = row[0]
            return send_file(io.BytesIO(qr_binary), mimetype='image/png')

        return "❌ No QR code found for this ID!"

    except Exception as e:
        return f"❌ Error: {e}"

# Route: Delete Record
@app.route('/delete/<id_number>')
def delete_record(id_number):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM dbo.QR WHERE id = ?", (id_number,))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))  # Refresh the page after deletion

    except Exception as e:
        return f"❌ Error: {e}"

@app.route('/edit/<id_number>', methods=['POST'])
def edit_record(id_number):
    new_name = request.form['name']
    new_id = request.form['new_id']

    if not new_id.isdigit() or len(new_id) != 4:
        return "❌ Please enter a valid 4-digit number!"

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        qr_binary = generate_qr(new_id)  # Generate new QR code

        cursor.execute("UPDATE dbo.QR SET name = ?, id = ?, qr = ? WHERE id = ?", 
                       (new_name, int(new_id), pyodbc.Binary(qr_binary), id_number))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    except Exception as e:
        return f"❌ Error: {e}"


# Run Flask App
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
