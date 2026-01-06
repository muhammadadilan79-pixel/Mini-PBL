from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import json
from database import init_db, get_db_connection
from scanner import scan_directory
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    paths = conn.execute('SELECT * FROM monitored_paths').fetchall()
    
    recent_scans = conn.execute('SELECT * FROM scan_logs ORDER BY scan_time DESC LIMIT 5').fetchall()
    
    conn.close()
    return render_template('index.html', paths=paths, scans=recent_scans)

@app.route('/add', methods=['POST'])
def add_path():
    path = request.form['path']
    if not os.path.exists(path):
        flash('Path does not exist!', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO monitored_paths (path) VALUES (?)', (path,))
        conn.commit()
        flash('Path added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Path is already being monitored.', 'warning')
    finally:
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/delete/<int:path_id>', methods=['POST'])
def delete_path(path_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM monitored_paths WHERE id = ?', (path_id,))
    conn.execute('DELETE FROM file_baselines WHERE path_id = ?', (path_id,))
    conn.commit()
    conn.close()
    flash('Path removed.', 'success')
    return redirect(url_for('index'))

@app.route('/scan/<int:path_id>')
def scan(path_id):
    conn = get_db_connection()
    path_row = conn.execute('SELECT * FROM monitored_paths WHERE id = ?', (path_id,)).fetchone()
    
    if not path_row:
        flash('Path not found.', 'error')
        conn.close()
        return redirect(url_for('index'))
    
    path = path_row['path']
    
    try:
        changes = scan_directory(path_id, path)
        status = "Clean"
        if changes['added'] or changes['modified'] or changes['deleted']:
            status = "Changes Detected"
        
        changes_json = json.dumps(changes)
        conn.execute('INSERT INTO scan_logs (status, details) VALUES (?, ?)', (status, changes_json))
        conn.commit()
        
        flash(f'Scan completed for {path}. Status: {status}', 'success')
    except Exception as e:
        flash(f'Error during scan: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('index'))

@app.route('/log/<int:log_id>')
def view_log(log_id):
    conn = get_db_connection()
    log = conn.execute('SELECT * FROM scan_logs WHERE id = ?', (log_id,)).fetchone()
    conn.close()
    
    if log:
        details = json.loads(log['details'])
        return render_template('scan_result.html', log=log, details=details)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
