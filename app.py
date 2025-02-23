from flask import Flask, render_template, request, jsonify, send_file
import pymysql
import pandas as pd
import os
import io
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

app = Flask(__name__)

# MySQL Database Connection

# Route to serve the dashboard

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Route to serve Add Product Page
@app.route('/add_product')
def add_product():
    return render_template('add_product.html')

# Route to serve Bulk Upload Page
@app.route('/bulk_upload')
def bulk_upload():
    return render_template('bulk_upload.html')

# Route to serve Search Page
@app.route('/search_page')
def search_page():
    return render_template('search.html')

@app.route('/print_page')
def print_page():
    return render_template('print.html')


# API to add a single product

# API to handle bulk upload
db = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
    port=int(os.getenv("MYSQL_PORT", 3306)),  # Default to 3306
    cursorclass=pymysql.cursors.DictCursor
)

# API to add a single product
@app.route('/add_product', methods=['POST'])
def add_product_api():
    data = request.json
    part_no = data.get("part_no")
    part_name = data.get("part_name")
    customer = data.get("customer")

    if not part_no or not part_name or not customer:
        return jsonify({"error": "All fields are required"}), 400

    try:
        with db.cursor() as cursor:
            sql = "INSERT INTO products (part_no, part_name, customer) VALUES (%s, %s, %s)"
            cursor.execute(sql, (part_no, part_name, customer))
            db.commit()
        return jsonify({"message": "Product added successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API to handle bulk upload
@app.route('/preview_bulk_upload', methods=['POST'])
def preview_bulk_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        df = pd.read_excel(file)
        df = df.iloc[:, ::-1]  # Flip column order ONCE

        json_data = df.to_dict(orient="records")
        return jsonify(json_data)  # Return reversed data for preview
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API to upload bulk data to MySQL
@app.route('/upload_bulk_data', methods=['POST'])
def upload_bulk_data():
    try:
        data = request.json.get("data")
        if not data:
            return jsonify({"error": "No data received"}), 400

        with db.cursor() as cursor:
            for row in data:
                part_no = row.get("PART NO.")
                part_name = row.get("PART NAME")
                customer = row.get("CUSTOMER")

                if not part_no or not part_name or not customer:
                    continue  # Skip rows with missing data

                sql = "INSERT INTO products (part_no, part_name, customer) VALUES (%s, %s, %s)"
                cursor.execute(sql, (part_no, part_name, customer))

            db.commit()

        return jsonify({"message": "Bulk upload successful!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# API to search for products
@app.route('/search', methods=['GET'])
def search_product():
    part_no = request.args.get('part_no', '')
    part_name = request.args.get('part_name', '')
    customer = request.args.get('customer', '')

    try:
        with db.cursor() as cursor:
            sql = """SELECT * FROM products 
                     WHERE part_no LIKE %s 
                     AND part_name LIKE %s
                     AND customer LIKE %s"""
            cursor.execute(sql, (f"%{part_no}%", f"%{part_name}%", f"%{customer}%"))
            result = cursor.fetchall()
            print("Search results:", result)  # Debugging
        return jsonify(result)
    except Exception as e:
        print("Error:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500
            
@app.route('/suggestions', methods=['GET'])
def get_suggestions():
    field = request.args.get('field', '')
    query = request.args.get('query', '')

    if field not in ["part_no", "part_name", "customer"] or not query:
        return jsonify([])

    try:
        with db.cursor() as cursor:
            sql = f"SELECT DISTINCT {field} FROM products WHERE {field} LIKE %s LIMIT 10"
            cursor.execute(sql, (f"%{query}%",))
            results = [row[field] for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/sticker_search', methods=['GET'])
def sticker_search():
    part_no = request.args.get('part_no', '')
    try:
        with db.cursor() as cursor:
            sql = "SELECT part_no, part_name, customer FROM products WHERE part_no LIKE %s LIMIT 20"
            cursor.execute(sql, (f"%{part_no}%",))
            result = cursor.fetchall()

        if result:
            return jsonify(result)  # Return all matching results
        else:
            return jsonify([])  # Return empty list instead of an error
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate_sticker_pdf', methods=['POST'])
def generate_sticker_pdf():
    data = request.json
    part_no = data['part_no']
    bill_no = data['bill_no']
    quantity = data['quantity']
    boxes = int(data['boxes'])

    # PDF settings: 8 cm × 5 cm in points (1 cm = 28.35 pts)
    width, height = 226.8, 141.7  

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))

    # Load Logo Image
    logo_path = "static/logo.png"  # Ensure this file exists
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
    else:
        logo = None  # Handle missing logo case

    for i in range(1, boxes + 1):  # Iterate through all boxes in sequence
        pdf.setFillColorRGB(1, 1, 1)  # White background
        pdf.rect(0, 0, width, height, fill=1)  # Full white background rectangle

        # Draw Logo if available
        if logo:
            pdf.drawImage(logo, 10, height - 50, width=80, height=30)  # Adjust position

        # Set text properties
        pdf.setFillColorRGB(0, 0, 0)  # Black text
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, height - 20, "OMCO ENTERPRISES LTD.")

        # Draw underlined company name
        pdf.line(100, height - 22, width - 20, height - 22)

        # Product details
        pdf.setFont("Helvetica", 10)
        pdf.drawString(20, height - 50, f"Part No.: {part_no}")
        pdf.drawString(20, height - 65, f"Bill No.: {bill_no}")
        pdf.drawString(20, height - 80, f"Quantity: {quantity} NOS")
        pdf.drawString(20, height - 95, "To: CNH INDUSTRIAL INDIA PVT. LTD.")

        # Add Box Number in bold
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(20, height - 115, f"Box No. {i} of {boxes}")

        pdf.showPage()  # Move to the next page for the next sticker

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="stickers.pdf", mimetype='application/pdf')

@app.route('/save_sticker_data', methods=['POST'])
def save_sticker_data():
    data = request.json
    part_no = data.get("part_no")
    part_name = data.get("part_name")
    customer = data.get("customer")
    qty=data.get("qty")
    bill_no = data.get("bill_no")
    boxes = data.get("boxes")
    timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

    if not part_no or not part_name or not customer or not bill_no or not boxes:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        with db.cursor() as cursor:
            sql = """
                INSERT INTO savedata (part_no, part_name, customer, qty, bill_no, boxes, date_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (part_no, part_name, customer, qty, bill_no, boxes, timestamp))
            db.commit()
        return jsonify({"message": "Sticker data saved successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/saved_data')
def saved_data():
    return render_template('saved_data.html')

@app.route('/get_saved_data', methods=['GET'])
def get_saved_data():
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM savedata ORDER BY date_time DESC")
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/input')
def input_page():
    return render_template('input.html')


if __name__ == '__main__':
    app.run(debug=True)