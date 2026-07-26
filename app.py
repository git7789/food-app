from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import random
from datetime import datetime
import hmac
import hashlib
import os
import json

# Serve static files from the current folder
app = Flask(__name__, static_folder='.')
CORS(app)

SECRET_KEY = b"my_super_secret_foodies_key_2026"
DB_FILE = "foodies_db.json"

# --- STAFF SECURITY CREDENTIALS ---
STAFF_USERNAME = "staff"
STAFF_PIN = "2026"
STAFF_PAGES = ['kds.html', 'dispatch.html', 'counter.html', 'board.html']

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
    {"id": 5, "name": "Nash Hot Wings", "description": "Crispy wings tossed in our fiery house sauce.", "price": 5.00, "category": "Wings", "image": "https://freepngimg.com/thumb/chicken/22156-3-fried-chicken-transparent-background.png", "in_stock": True},
    {"id": 6, "name": "Honey BBQ Wings", "description": "Sweet and smoky BBQ glazed wings.", "price": 5.00, "category": "Wings", "image": "https://freepngimg.com/thumb/meat/33946-8-chicken-wings-photos.png", "in_stock": True},
    {"id": 12, "name": "Street Fries", "description": "Loaded fries with cheese sauce and jalapeños.", "price": 3.50, "category": "Sides", "image": "https://freepngimg.com/thumb/french_fries/5-2-french-fries-png-hd.png", "in_stock": True},
    {"id": 13, "name": "Onion Rings", "description": "Beer-battered onion rings with dip.", "price": 2.50, "category": "Sides", "image": "https://freepngimg.com/thumb/onion/140810-ring-onion-png-download-free.png", "in_stock": True},
    {"id": 15, "name": "Vanilla Shake", "description": "Thick hand-spun vanilla shake.", "price": 3.00, "category": "Drinks", "image": "https://freepngimg.com/thumb/milkshake/25692-3-milkshake-file.png", "in_stock": True},
    {"id": 17, "name": "Cola", "description": "Ice cold can.", "price": 1.00, "category": "Drinks", "image": "https://freepngimg.com/thumb/coca_cola/2-2-coca-cola-png-hd.png", "in_stock": True}
]

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                return data.get('orders', {}), data.get('menu', default_menu), data.get('users', {})
        except Exception as e:
            print(f"[WARNING] Could not load DB, starting fresh. Error: {e}")
    return {}, default_menu, {}

def save_db():
    try:
        with open(DB_FILE, 'w') as f:
            json.dump({"orders": orders_db, "menu": menu_db, "users": users_db}, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Failed to save DB: {e}")

# Load memory on startup
orders_db, menu_db, users_db = load_db()

@app.route('/', methods=['GET'])
def home():
    return send_from_directory('.', 'index.html')

# --- Customer Authentication ---
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        if username in users_db:
            return jsonify({"error": "Username already exists"}), 400
            
        users_db[username] = {
            "username": username,
            "password": hash_password(password),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_db()
        return jsonify({"message": "Account created successfully", "username": username}), 201
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

@app.route('/api/menu', methods=['POST'])
def add_menu_item():
    try:
        data = request.json
        new_id = max([item['id'] for item in menu_db]) + 1 if menu_db else 1
        new_item = {
            "id": new_id,
            "name": data.get('name'),
            "description": data.get('description'),
            "price": float(data.get('price')),
            "category": data.get('category'),
            "image": data.get('image'),
            "in_stock": True
        }
        menu_db.append(new_item)
        save_db()
        return jsonify({"message": "Item added!", "item": new_item}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/menu/<int:item_id>', methods=['PUT'])
def toggle_stock(item_id):
    for item in menu_db:
        if item['id'] == item_id:
            item['in_stock'] = not item['in_stock']
            save_db()
            return jsonify({"message": "Stock status updated", "item": item}), 200
    return jsonify({"error": "Item not found"}), 404

@app.route('/api/menu/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    global menu_db
    menu_db = [item for item in menu_db if item['id'] != item_id]
    save_db()
    return jsonify({"message": "Item deleted"}), 200

# --- Order Core Logic ---
@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.json
        customer_name = data.get('name')
        account_username = data.get('account_username') 
        cart_items = data.get('items')
        total_price = data.get('total')

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
        print(f"[ORDER PAID] #{order_id} saved. Waiting for customer arrival.")
        
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
        print(f"[ARRIVAL] #{order_id} scanned. Ticket sent to Kitchen!")
        
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
            print(f"[SYSTEM SWEEP] #{order_id} removed.")
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
            print(f"[READY] #{order_id} is assembled.")
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
            print(f"[UNDO] #{order_id} reverted back to kitchen.")
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
                print(f"[DISPATCHED] #{order_id} handed to customer.")
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

# --- SERVE HTML PAGES WITH STAFF SECURITY ---
@app.route('/<path:filename>')
def serve_html(filename):
    if filename in STAFF_PAGES:
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # If running in a cloud environment (like Render), it will use the PORT variable
    # If running locally, it defaults to 5000 with the adhoc SSL
    if os.environ.get('RENDER'):
        app.run(host='0.0.0.0', port=port)
    else:
        print(f"🚀 Foodies System running locally on Port {port} (SECURE HTTPS)")
        print(f"🔒 Staff pages protected. Username: {STAFF_USERNAME} | PIN: {STAFF_PIN}")
        app.run(host='0.0.0.0', debug=True, port=port, ssl_context='adhoc')