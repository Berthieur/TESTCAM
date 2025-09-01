from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import os
import time
from datetime import datetime

# --- Importation des fonctions de la base de données ---
# Assurez-vous d'avoir le fichier database.py dans le même répertoire
from database import init_db, get_db

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- Initialisation de la base de données ---
init_db()

# --- Filtres Jinja2 pour le template ---
def timestamp_to_datetime(timestamp):
    """Convertit un timestamp en millisecondes en une date lisible."""
    try:
        return datetime.fromtimestamp(timestamp / 1000).strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return '-'
app.jinja_env.filters['timestamp_to_datetime'] = timestamp_to_datetime

# --- Routes API ---

# 1. 🔐 Login (exemple simple)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if data.get('username') == 'admin' and data.get('password') == '1234':
        return jsonify({
            "token": "fake-jwt-token-123",
            "role": "admin",
            "userId": "ADMIN001"
        })
    return jsonify({"error": "Identifiants invalides"}), 401

# 2. 👥 Enregistrement employé
@app.route('/api/employees', methods=['POST'])
def register_employee():
    emp = request.get_json()
    required = ['id', 'nom', 'prenom', 'type']
    for field in required:
        if field not in emp:
            return jsonify({"error": f"Champ manquant: {field}"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO employees 
        (id, nom, prenom, date_naissance, lieu_naissance, telephone, email, profession,
         type, taux_horaire, frais_ecolage, qr_code, is_active, created_at, is_synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    ''', [
        emp['id'],
        emp['nom'],
        emp['prenom'],
        emp.get('dateNaissance'),
        emp.get('lieuNaissance'),
        emp.get('telephone'),
        emp.get('email'),
        emp.get('profession'),
        emp['type'],
        emp.get('tauxHoraire'),
        emp.get('fraisEcolage'),
        emp.get('qrCode'),
        emp.get('isActive', True),
        emp.get('createdAt', int(time.time() * 1000))
    ])
    conn.commit()
    return jsonify({"status": "success", "message": "Employé enregistré"}), 201

# 3. 📋 Liste de tous les employés
@app.route('/api/employees', methods=['GET'])
def get_all_employees():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees ORDER BY nom, prenom")
    employees = [dict(row) for row in cursor.fetchall()]
    return jsonify(employees)

# 4. 👷 Employés actifs
@app.route('/api/employees/active', methods=['GET'])
def get_active_employees():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE is_active = 1 ORDER BY nom")
    return jsonify([dict(row) for row in cursor.fetchall()])

# 5. 📍 Position (dernier pointage)
@app.route('/api/employees/<employeeId>/position', methods=['GET'])
def get_employee_position(employeeId):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT employee_id, employee_name, type, timestamp, date
        FROM pointages
        WHERE employee_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', [employeeId])
    row = cursor.fetchone()
    if row:
        return jsonify(dict(row))
    return jsonify({"error": "Aucun pointage trouvé"}), 404

# 6. 💰 Enregistrer un salaire
@app.route('/api/salary', methods=['POST'])
def save_salary_record():
    record = request.get_json()
    required = ['employeeId', 'employeeName', 'type', 'amount', 'period', 'date']
    for field in required:
        if field not in record:
            return jsonify({"error": f"Champ manquant: {field}"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO salaries 
        (id, employee_id, employee_name, type, amount, hours_worked, period, date, is_synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', [
        record.get('id', str(int(record['date']))),
        record['employeeId'],
        record['employeeName'],
        record['type'],
        record['amount'],
        record.get('hoursWorked'),
        record['period'],
        record['date']
    ])
    conn.commit()
    return jsonify({"status": "success", "id": cursor.lastrowid}), 201

# 7. 📅 Historique des salaires
@app.route('/api/salary/history', methods=['GET'])
def get_salary_history():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM salaries ORDER BY date DESC")
    return jsonify([dict(row) for row in cursor.fetchall()])

# 8. 📊 Statistiques par zone (exemple fictif)
@app.route('/api/statistics/zones/<employeeId>', methods=['GET'])
def get_zone_statistics(employeeId):
    return jsonify([
        {"zone_name": "Zone A", "duration_seconds": 2700},
        {"zone_name": "Zone B", "duration_seconds": 1800}
    ])

# 9. 🚶 Historique des mouvements (pointages)
@app.route('/api/movements/<employeeId>', methods=['GET'])
def get_movement_history(employeeId):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT employee_id, employee_name, type, timestamp, date
        FROM pointages
        WHERE employee_id = ?
        ORDER BY timestamp DESC
    ''', [employeeId])
    return jsonify([dict(row) for row in cursor.fetchall()])

# 10. ⚠️ Alerte zone interdite
@app.route('/api/alerts/forbidden-zone', methods=['POST'])
def report_forbidden_zone():
    alert = request.get_json()
    required = ['employeeId', 'employeeName', 'zoneName', 'timestamp']
    for field in required:
        if field not in alert:
            return jsonify({"error": f"Champ manquant: {field}"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO alerts (employeeId, employeeName, zone_name, timestamp)
        VALUES (?, ?, ?, ?)
    ''', [
        alert['employeeId'],
        alert['employeeName'],
        alert['zoneName'],
        alert['timestamp']
    ])
    conn.commit()
    return jsonify({"status": "alerte_enregistrée"}), 201

# 11. 📡 État ESP32
@app.route('/api/esp32/status', methods=['GET'])
def get_esp32_status():
    return jsonify({
        "is_online": True,
        "last_seen": int(time.time() * 1000),
        "firmware_version": "1.2.0",
        "uptime_seconds": 3672
    })

# 12. 🔊 Activer le buzzer
@app.route('/api/esp32/buzzer', methods=['POST'])
def activate_buzzer():
    data = request.get_json()
    duration = data.get('durationMs', 1000)
    return jsonify({
        "status": "buzzer_activé",
        "durationMs": duration,
        "timestamp": int(time.time() * 1000)
    })

# --- Nouvelles routes utiles ---

# 🔄 Synchronisation : Récupérer les données non synchronisées
@app.route('/api/sync/pointages', methods=['GET'])
def get_unsynced_pointages():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pointages WHERE is_synced = 0")
    return jsonify([dict(row) for row in cursor.fetchall()])

# 🔄 Envoyer des pointages depuis Android
@app.route('/api/pointages', methods=['POST'])
def add_pointage():
    p = request.get_json()
    required = ['id', 'employeeId', 'employeeName', 'type', 'timestamp', 'date']
    for field in required:
        if field not in p:
            return jsonify({"error": f"Champ manquant: {field}"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO pointages 
        (id, employee_id, employee_name, type, timestamp, date, is_synced)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    ''', [
        p['id'],
        p['employeeId'],
        p['employeeName'],
        p['type'],
        p['timestamp'],
        p['date']
    ])
    conn.commit()
    return jsonify({"status": "pointage_enregistré"}), 201

# 📥 Télécharger tous les pointages (pour mise à jour locale)
@app.route('/api/pointages', methods=['GET'])
def get_all_pointages():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pointages ORDER BY timestamp DESC")
    return jsonify([dict(row) for row in cursor.fetchall()])

# 💸 Liste des employés avec leurs paiements
@app.route('/api/employee_payments', methods=['GET'])
def get_employee_payments():
    try:
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.nom, e.prenom, e.type, s.employee_name, s.type AS payment_type, 
                   s.amount, s.period, s.date
            FROM employees e
            LEFT JOIN salaries s ON e.id = s.employee_id
            WHERE e.is_active = 1
            ORDER BY s.date DESC
        ''')
        payments = [dict(row) for row in cursor.fetchall()]
        return jsonify(payments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 📊 Tableau de bord HTML - CORRIGÉ
@app.route('/dashboard', methods=['GET'])
def dashboard():
    try:
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Requête modifiée pour utiliser INNER JOIN afin d'afficher uniquement les paiements existants.
        cursor.execute('''
            SELECT e.nom, e.prenom, e.type, s.employee_name, s.type AS payment_type, 
                   s.amount, s.period, s.date
            FROM salaries s
            INNER JOIN employees e ON e.id = s.employee_id
            WHERE e.is_active = 1
            ORDER BY s.date DESC
        ''')
        payments = [dict(row) for row in cursor.fetchall()]
        return render_template('dashboard.html', payments=payments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Démarrage ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
