import os
import hashlib
from database import get_db_connection

def calculate_hash(file_path):
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (OSError, PermissionError):
        return None

def scan_directory(path_id, directory_path):
    """Scans a directory and returns changes."""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT file_path, file_hash FROM file_baselines WHERE path_id = ?", (path_id,))
    baseline = directory_to_dict(c.fetchall())

    current_files = {}
    changes = {
        "added": [],
        "modified": [],
        "deleted": []
    }

    for root, _, files in os.walk(directory_path):
        for file in files:
            full_path = os.path.join(root, file)
            file_hash = calculate_hash(full_path)
            
            if file_hash:
                current_files[full_path] = file_hash

                if full_path not in baseline:
                    changes["added"].append(full_path)
                elif baseline[full_path] != file_hash:
                    changes["modified"].append(full_path)

    for file_path in baseline:
        if file_path not in current_files:
            changes["deleted"].append(file_path)

    c.execute("DELETE FROM file_baselines WHERE path_id = ?", (path_id,))
    
    new_records = [(path_id, path, h) for path, h in current_files.items()]
    if new_records:
        c.executemany("INSERT INTO file_baselines (path_id, file_path, file_hash) VALUES (?, ?, ?)", new_records)

    conn.commit()
    conn.close()
    
    return changes

def directory_to_dict(rows):
    """Helper to convert DB rows to a dict {path: hash}."""
    return {row['file_path']: row['file_hash'] for row in rows}
