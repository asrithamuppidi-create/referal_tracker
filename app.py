from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATA_FILE = 'registrations.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {'registrations': {}, 'referrals': {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"message": "API running!", "status": "online"})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({"error": "Name required"}), 400
    
    # Load existing data
    db = load_data()
    
    # Check if name already exists
    for code, info in db['registrations'].items():
        if info['name'].lower() == name.lower():
            return jsonify({"error": "Name already registered"}), 400
    
    # Generate unique code
    code = str(uuid.uuid4())[:8].upper()
    
    # Store registration
    db['registrations'][code] = {
        'name': name,
        'registered_at': datetime.now().isoformat(),
        'referrer_code': request.args.get('ref')
    }
    
    # Track referral if applicable
    referrer_code = request.args.get('ref')
    if referrer_code and referrer_code in db['registrations']:
        if referrer_code not in db['referrals']:
            db['referrals'][referrer_code] = 0
        db['referrals'][referrer_code] += 1
    
    save_data(db)
    
    return jsonify({"code": code, "name": name})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    db = load_data()
    total = len(db['registrations'])
    
    return jsonify({
        "total_registrations": total,
        "total_referrals": sum(db['referrals'].values()),
        "remaining_capacity": max(0, 500 - total)
    })

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    db = load_data()
    limit = request.args.get('limit', default=10, type=int)
    
    # Build leaderboard
    leaderboard = []
    for code, count in db['referrals'].items():
        if code in db['registrations']:
            leaderboard.append({
                'name': db['registrations'][code]['name'],
                'code': code,
                'referral_count': count
            })
    
    # Sort by referral count descending
    leaderboard.sort(key=lambda x: x['referral_count'], reverse=True)
    
    return jsonify({"leaderboard": leaderboard[:limit]})

@app.route('/api/check-name', methods=['GET'])
def check_name():
    name = request.args.get('name', '').strip()
    db = load_data()
    
    exists = any(info['name'].lower() == name.lower() for info in db['registrations'].values())
    return jsonify({"exists": exists})

@app.route('/api/referrer/<code>', methods=['GET'])
def get_referrer(code):
    db = load_data()
    
    if code in db['registrations']:
        return jsonify({
            "name": db['registrations'][code]['name'],
            "referral_count": db['referrals'].get(code, 0)
        })
    
    return jsonify({"error": "Referrer not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
