import pymysql
import sys

def create_db(password):
    try:
        print(f"Connecting with password: '{password}'...")
        conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password=password, charset='utf8mb4')
        cursor = conn.cursor()
        print("Creating database 'sistema_buap_db'...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS sistema_buap_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print("Database created successfully!")
        conn.close()
        return True
    except Exception as e:
        print(f"Failed with password '{password}': {e}")
        return False

if not create_db(''):
    if not create_db('changocome'):
        print("Could not create database with empty password or 'changocome'.")
        sys.exit(1)
