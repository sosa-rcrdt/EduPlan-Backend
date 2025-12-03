import pymysql

try:
    print("Connecting to database...")
    conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='', charset='utf8mb4')
    cursor = conn.cursor()
    
    print("Flushing privileges...")
    cursor.execute("FLUSH PRIVILEGES;")
    
    print("Altering user...")
    # Try both syntaxes just in case, but usually one works.
    # For MariaDB/MySQL 5.7+:
    try:
        cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('changocome');")
    except Exception as e:
        print(f"Error altering user (method 1): {e}")
        # Fallback for older versions or different syntax
        cursor.execute("SET PASSWORD FOR 'root'@'localhost' = PASSWORD('changocome');")
        
    print("Flushing privileges again...")
    cursor.execute("FLUSH PRIVILEGES;")
    
    conn.close()
    print("Fixed successfully!")
except Exception as e:
    print(f"Failed: {e}")
