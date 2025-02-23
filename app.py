from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
import io
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

app = Flask(__name__)
PRODUCTS_FILE = 'products.xlsx'
SAVED_DATA_FILE = 'savedata.xlsx'

# Excel file path
if not os.path.exists(PRODUCTS_FILE):
    df = pd.DataFrame(columns=['part_no', 'part_name', 'customer'])
    df.to_excel(PRODUCTS_FILE, index=False)

# Ensure the saved sticker data file exists
if not os.path.exists(SAVED_DATA_FILE):
    df = pd.DataFrame(columns=['part_no', 'part_name', 'customer', 'qty', 'bill_no', 'boxes', 'date_time'])
    df.to_excel(SAVED_DATA_FILE, index=False)

# Route to serve the dashboard
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Route to serve Add Product Page
@app.route('/product')
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
@app.route('/add_product', methods=['POST'])
def add_product_api():
    try:
        data = request.get_json()
        print("Received Data:", data)  # Debugging

        part_no = data.get("part_no")
        part_name = data.get("part_name")
        customer = data.get("customer")

        if not part_no or not part_name or not customer:
            return jsonify({"error": "All fields are required"}), 400

        df = pd.read_excel(PRODUCTS_FILE)
        new_row = {'part_no': part_no, 'part_name': part_name, 'customer': customer}
        
        
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        df.to_excel(PRODUCTS_FILE, index=False)

        return jsonify({"message": "Product added successfully!"})
    except Exception as e:
        print("Error:", str(e))  # Debugging
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

# API to upload bulk data to Excel
@app.route('/upload_bulk_data', methods=['POST'])
def upload_bulk_data():
    try:
        data = request.json.get("data")
        if not data:
            return jsonify({"error": "No data received"}), 400

        df = pd.read_excel(PRODUCTS_FILE)  # Load existing data

        for row in data:
            part_no = row.get("PART NO.")  # Ensure column names match
            part_name = row.get("PART NAME")
            customer = row.get("CUSTOMER")

            if not part_no or not part_name or not customer:
                continue  # Skip rows with missing data

            new_row = {'part_no': part_no, 'part_name': part_name, 'customer': customer}
            
          
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        df.to_excel(PRODUCTS_FILE, index=False)  # Save back to products.xlsx

        return jsonify({"message": "Bulk upload successful!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# API to search for products
@app.route('/search', methods=['GET'])
def search_product():
    part_no = request.args.get('part_no', '').strip()
    part_name = request.args.get('part_name', '').strip()
    customer = request.args.get('customer', '').strip()

    try:
        df = pd.read_excel(PRODUCTS_FILE)
        df = df.astype(str)  # Convert all fields to string to prevent NaN issues

        # Apply filters only if values are provided
        if part_no:
            df = df[df['part_no'].str.contains(part_no, case=False, na=False)]
        if part_name:
            df = df[df['part_name'].str.contains(part_name, case=False, na=False)]
        if customer:
            df = df[df['customer'].str.contains(customer, case=False, na=False)]

        result = df.to_dict(orient="records")
        print("Search Results:", result)  # Debugging

        return jsonify(result)
    except Exception as e:
        print("Search API Error:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500
            
@app.route('/suggestions', methods=['GET'])
def get_suggestions():
    field = request.args.get('field', '')
    query = request.args.get('query', '')
    print(field)
    print(query)

    if field not in ["part_no", "part_name", "customer"] or not query:
        return jsonify([])

    try:
        df = pd.read_excel(PRODUCTS_FILE)
        print(df)
        df[field] = df[field].astype(str)  # Ensure all values are strings
        results = df[df[field].str.contains(query, case=False, na=False)][field].unique().tolist()
        print(results)
        return jsonify(results[:10])  # Limit to 10 suggestions
    except Exception as e:
        print("Error in suggestions API:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500
    
@app.route('/sticker_search', methods=['GET'])
def sticker_search():
    part_no = request.args.get('part_no', '').strip()

    if not part_no:
        return jsonify([])

    try:
        df = pd.read_excel(PRODUCTS_FILE)
        df = df.astype(str)  # Convert all fields to string to prevent NaN issues

        # Filter the dataframe based on part number
        filtered_df = df[df['part_no'].str.contains(part_no, case=False, na=False)]

        results = filtered_df[['part_no', 'part_name']].to_dict(orient="records")
        print("Sticker Search Results:", results)  # Debugging

        return jsonify(results[:10])  # Limit to 10 results
    except Exception as e:
        print("Error in sticker search API:", str(e))  # Debugging
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
    qty = data.get("qty")
    bill_no = data.get("bill_no")
    boxes = data.get("boxes")
    timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

    if not part_no or not part_name or not customer or not bill_no or not boxes:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Load existing data from savedata.xlsx
        df = pd.read_excel(SAVED_DATA_FILE)

        # Create a new row
        new_row = pd.DataFrame([{
            'part_no': part_no, 
            'part_name': part_name, 
            'customer': customer, 
            'qty': qty, 
            'bill_no': bill_no, 
            'boxes': boxes, 
            'date_time': timestamp
        }])

        # Use pd.concat() instead of append()
        df = pd.concat([df, new_row], ignore_index=True)

        # Save back to Excel
        df.to_excel(SAVED_DATA_FILE, index=False)

        return jsonify({"message": "Sticker data saved successfully!"})
    except Exception as e:
        print("Error saving sticker data:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500

@app.route('/saved_data')
def saved_data():
    return render_template('saved_data.html')

@app.route('/get_saved_data', methods=['GET'])
def get_saved_data():
    try:
        df = pd.read_excel(SAVED_DATA_FILE)
        result = df.to_dict(orient="records")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/input')
def input_page():
    return render_template('input.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)