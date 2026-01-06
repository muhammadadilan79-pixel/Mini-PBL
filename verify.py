import os
import shutil
import time
from app import app
from database import init_db, get_db_connection
from scanner import scan_directory

TEST_DIR = "test_data"
if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(TEST_DIR)

if os.path.exists("integrity.db"):
    os.remove("integrity.db")
init_db()

def create_file(name, content):
    with open(os.path.join(TEST_DIR, name), "w") as f:
        f.write(content)

def verify():
    print("Starting verification...")
    
    create_file("file1.txt", "v1")
    create_file("file2.txt", "v1")
    
    conn = get_db_connection()
    conn.execute('INSERT INTO monitored_paths (path) VALUES (?)', (os.path.abspath(TEST_DIR),))
    path_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    
    print(f"Path added with ID: {path_id}")

    print("Running baseline scan...")
    changes = scan_directory(path_id, os.path.abspath(TEST_DIR))
    print(f"Baseline changes (should be added): {changes}")
    assert len(changes['added']) == 2
    assert len(changes['modified']) == 0
    assert len(changes['deleted']) == 0

    print("Modifying files...")
    time.sleep(1)
    create_file("file1.txt", "v2")
    os.remove(os.path.join(TEST_DIR, "file2.txt"))
    create_file("file3.txt", "v1")

    print("Running second scan...")
    changes = scan_directory(path_id, os.path.abspath(TEST_DIR))
    print(f"Second scan changes: {changes}")
    
    assert len(changes['added']) == 1
    assert "file3.txt" in changes['added'][0]
    
    assert len(changes['modified']) == 1
    assert "file1.txt" in changes['modified'][0]
    
    assert len(changes['deleted']) == 1
    assert "file2.txt" in changes['deleted'][0]
    
    print("Verification SUCCESS!")

if __name__ == "__main__":
    try:
        verify()
    finally:
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)
        if os.path.exists("integrity.db"):
            os.remove("integrity.db")
