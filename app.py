from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import random
from datetime import datetime
import hmac
import hashlib
import os
import json
from pymongo import MongoClient

app = Flask(__name__, static_folder='.')
CORS(app)

SECRET_KEY = b"my_super_secret_foodies_key_2026"
DB_FILE = "foodies_db.json"

# --- CLOUD DATABASE SETUP (MongoDB) ---
# The server will automatically look for this environment variable
MONGO_URI = os.environ.get("MONGO_URI")
try:
    if MONGO_URI:
        client = MongoClient(MONGO_URI)
        db = client["foodies_cloud"]
        cloud_state = db["app_state"]
        print("[SYSTEM] Connected to MongoDB Cloud successfully!")
    else:
        print("[WARNING] MONGO_URI not found. Using local ephemeral memory.")
        cloud_state = None
except Exception as e:
    print(f"[ERROR] MongoDB Connection Failed: {e}")
    cloud_state = None

# --- STAFF SECURITY CREDENTIALS ---
STAFF_USERNAME = "staff"
STAFF_PIN = "2026"
STAFF_PAGES = ['kds.html', 'dispatch.html', 'counter.html', 'board.html']

# --- TEMPORARY MEMORY FOR EMAIL VERIFICATION ---
pending_verifications = {}

def check_auth(username, password):
    return username == STAFF_USERNAME and password == STAFF_PIN

def authenticate():
    return Response(
    'RESTRICTED AREA: You must login with proper staff credentials to access this system.', 401,
    {'WWW-Authenticate': 'Basic realm="Foodies Internal System"'})

def generate_signature(order_id):
    return hmac.new(SECRET_KEY, str(order_id).encode(), hashlib.sha256).hexdigest()[:10]

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Database Persistence Logic ---
default_menu = [
    {"id": 1, "name": "The Hustler Burger", "description": "Double beef patty, signature sauce, caramelized onions.", "price": 6.50, "category": "Burgers", "image": "https://freepngimg.com/thumb/burger/5-2-burger-png.png", "in_stock": True},
    {"id": 2, "name": "Classic Cheese", "description": "Single beef patty, cheddar slice, pickles, ketchup.", "price": 4.50, "category": "Burgers", "image": "https://freepngimg.com/thumb/burger/2-2-burger-free-download-png.png", "in_stock": True},
    {"id": 3, "name": "Crispy Chicken", "description": "Fried chicken breast, ranch dressing, lettuce, tomato.", "price": 5.50, "category": "Burgers", "image": "https://freepngimg.com/thumb/burger/6-2-burger-png-image.png", "in_stock": True},
    {"id": 5, "name": "Nash Hot Wings", "description": "Crispy wings tossed in our fiery house sauce.", "price": 5.00, "category": "Wings", "image": "https://freepngimg.com/thumb/chicken/22156-3-fried-chicken-transparent-background.png", "in_stock": True}
]

def load_db():
    if cloud_state is not None:
        try:
            record = cloud_state.find_one({"_id": "main_state"})
            if record:
                return record.get('orders', {}), record.get('menu', default_menu), record.get('users', {})
        except Exception as e:
            print(f"[ERROR] Could not load from Mongo: {e}")
            
    # Fallback to local JSON if Mongo fails or is not configured locally
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                return data.get('orders', {}), data.get('menu', default_menu), data.get('users', {})
        except Exception as e:
            print(f"[WARNING] Could not load DB, starting fresh. Error: {e}")
    return {}, default_menu, {}

def save_db():
    if cloud_state is not None:
        try:
            cloud_state.update_one(
                {"_id": "main_state"},
                {"$set": {"orders": orders_db, "menu": menu_db, "users": users_db}},
                upsert=True
            )
            return
        except Exception as e:
            print(f"[ERROR] Failed to save to Mongo: {e}")
            
    # Fallback to local file saving
    try:
        with open(DB_FILE, 'w') as f:
            json.dump({"orders": orders_db, "menu": menu_db, "users": users_db}, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Failed to save DB: {e}")

orders_db, menu_db, users_db = load_db()

@app.route('/', methods=['GET'])
def home():
    return send_from_directory('.', 'index.html')

# --- Customer Authentication ---
@app.route('/api/auth/request-code', methods=['POST'])
def request_code():
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        
        if not email or not username:
            return jsonify({"error": "Email and username required"}), 400
            
        if username in users_db:
            return jsonify({"error": "Username already exists"}), 400
            
        # Check if email is already used
        for user in users_db.values():
            if user.get('email') == email:
                return jsonify({"error": "Email is already registered"}), 400

        # Generate a 6-digit verification code
        code = str(random.randint(100000, 999999))
        
        # Save to temporary memory
        pending_verifications[email] = code
        
        print(f"[SYSTEM] Verification code for {email} is: {code}")
        
        return jsonify({
            "message": "Verification code sent!", 
            "demo_code": code
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        code = data.get('code', '').strip()
        
        if not all([username, email, password, code]):
            return jsonify({"error": "All fields and verification code are required"}), 400
            
        # Verify the code
        expected_code = pending_verifications.get(email)
        if not expected_code or expected_code != code:
            return jsonify({"error": "Invalid or expired verification code"}), 400
            
        # Create the account
        users_db[username] = {
            "username": username,
            "email": email,
            "password": hash_password(password),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_db()
        
        # Clear the pending verification
        del pending_verifications[email]
        
        return jsonify({"message": "Account verified and created!", "username": username}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        user = users_db.get(username)
        if not user or user['password'] != hash_password(password):
            return jsonify({"error": "Invalid username or password"}), 401
            
        return jsonify({"message": "Login successful", "username": username}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Menu Management ---
@app.route('/api/menu', methods=['GET'])
def get_menu():
    return jsonify({"menu": menu_db}), 200

# --- Order Core Logic ---
@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.json
        customer_name = data.get('name')
        account_username = data.get('account_username') 
        cart_items = data.get('items')
        total_price = data.get('total')
        phone = data.get('phone') 

        if not all([customer_name, cart_items, total_price]):
            return jsonify({"error": "Missing order details"}), 400

        available_ids = [str(i) for i in range(100, 1000) if str(i) not in orders_db]
        
        if not available_ids:
            return jsonify({"error": "System at max capacity. Please clear old orders."}), 503
            
        order_id = random.choice(available_ids)
        current_time = datetime.now().strftime("%H:%M:%S")
        signature = generate_signature(order_id)
        qr_payload = f"FOODIES_ORDER:{order_id}:{signature}"
        
        new_order = {
            "id": order_id,
            "name": customer_name,
            "account_username": account_username,
            "items": cart_items,
            "total": total_price,
            "status": "waiting",
            "created_at": current_time,
            "qr_payload": qr_payload,
            "timestamp": int(datetime.now().timestamp() * 1000)
        }
        
        orders_db[order_id] = new_order
        save_db()

        # --- SMS NOTIFICATION SYSTEM ---
        if phone and len(phone) >= 9:
            qr_link = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=FOODIES_ORDER:{order_id}:{signature}"
            print(f"\n[SMS SENT to +263{phone[-9:]}]")
            print(f"Message: Foodies Order #{order_id} placed! Tap link for your QR ticket: {qr_link}\n")

        return jsonify({
            "message": "Payment Successful! Show code at counter.",
            "order_id": order_id,
            "qr_payload": qr_payload
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_active_orders():
    active_orders = [order for order in orders_db.values() if order['status'] == 'cooking']
    active_orders.sort(key=lambda x: x.get('scanned_at', x['created_at']))
    return jsonify({"active_orders": active_orders}), 200

@app.route('/api/waiting', methods=['GET'])
def get_waiting_orders():
    waiting_orders = [order for order in orders_db.values() if order['status'] == 'waiting']
    waiting_orders.sort(key=lambda x: x['created_at'])
    return jsonify({"waiting_orders": waiting_orders}), 200

@app.route('/api/scan', methods=['POST'])
def scan_qr_code():
    try:
        data = request.json
        scanned_payload = data.get('qr_payload') 
        parts = scanned_payload.split(":") 
        
        if parts[0] == "MANUAL_ENTRY" and len(parts) == 2:
            order_id = parts[1]
        elif parts[0] == "FOODIES_ORDER" and len(parts) == 3:
            order_id = parts[1]
            scanned_signature = parts[2]
            if scanned_signature != generate_signature(order_id):
                return jsonify({"error": "FRAUD ALERT: Fake QR Code!"}), 403
        else:
            return jsonify({"error": "Invalid format"}), 400
            
        if order_id not in orders_db:
            return jsonify({"error": "Order not found"}), 404
            
        order = orders_db[order_id]
        
        if order['status'] == 'cooking':
            return jsonify({"error": "Order already sent to kitchen!"}), 400
        if order['status'] in ['ready', 'collected']:
            return jsonify({"error": "Order is already completed!"}), 400
            
        order['status'] = 'cooking'
        order['scanned_at'] = datetime.now().strftime("%H:%M:%S")
        
        save_db()
        return jsonify({
            "message": "Arrival confirmed! Assembling order now.",
            "order": order
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sweep', methods=['POST'])
def sweep_order():
    try:
        data = request.json
        order_id = str(data.get('order_id'))
        if order_id in orders_db and orders_db[order_id]['status'] == 'waiting':
            del orders_db[order_id]
            save_db()
            return jsonify({"message": "Order swept!"}), 200
        return jsonify({"error": "Order not found or cannot be swept"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/complete', methods=['POST'])
def complete_order():
    try:
        data = request.json
        order_id = str(data.get('order_id')) 
        if order_id in orders_db:
            orders_db[order_id]['status'] = 'ready'
            save_db()
            return jsonify({"message": "Order marked ready!"}), 200
        return jsonify({"error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/undo', methods=['POST'])
def undo_order():
    try:
        data = request.json
        order_id = str(data.get('order_id')) 
        if order_id in orders_db and orders_db[order_id]['status'] == 'ready':
            orders_db[order_id]['status'] = 'cooking'
            save_db()
            return jsonify({"message": "Order reverted to cooking!"}), 200
        return jsonify({"error": "Order not found or cannot be undone"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear_order():
    try:
        data = request.json
        payload = data.get('qr_payload', '')
        order_id = str(data.get('order_id', ''))
        
        if "FOODIES_ORDER:" in payload:
            parts = payload.split(":")
            if len(parts) >= 2:
                order_id = parts[1]
        elif ":" in order_id:
            order_id = order_id.split(":")[0]
            
        order_id = order_id.replace("MANUAL_ENTRY:", "").replace("#", "").strip()

        if order_id in orders_db:
            if orders_db[order_id]['status'] == 'ready':
                orders_db[order_id]['status'] = 'collected'
                orders_db[order_id]['collected_at'] = datetime.now().strftime("%H:%M:%S")
                save_db()
                return jsonify({"success": True, "message": "Order collected!"}), 200
            else:
                current_status = orders_db[order_id]['status'].upper()
                return jsonify({"error": f"Ticket #{order_id} is currently {current_status}"}), 400
        
        return jsonify({"error": f"Ticket #{order_id} not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/board', methods=['GET'])
def get_board_status():
    preparing_orders = [order for order in orders_db.values() if order['status'] == 'cooking']
    ready_orders = [order for order in orders_db.values() if order['status'] == 'ready']
    
    preparing_orders.sort(key=lambda x: x.get('scanned_at', x['created_at']))
    ready_orders.sort(key=lambda x: x.get('created_at'))
    
    return jsonify({
        "preparing": preparing_orders,
        "ready": ready_orders
    }), 200

@app.route('/api/history', methods=['GET'])
def get_history():
    all_orders = list(orders_db.values())
    return jsonify({"all_orders": all_orders}), 200

@app.route('/api/user/history/<username>', methods=['GET'])
def get_user_history(username):
    user_orders = [order for order in orders_db.values() if order.get('account_username') == username]
    user_orders.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return jsonify({"history": user_orders}), 200

@app.route('/<path:filename>')
def serve_html(filename):
    if filename in STAFF_PAGES:
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    if os.environ.get('RENDER'):
        app.run(host='0.0.0.0', port=port)
    else:
        app.run(host='0.0.0.0', debug=True, port=port, ssl_context='adhoc')
