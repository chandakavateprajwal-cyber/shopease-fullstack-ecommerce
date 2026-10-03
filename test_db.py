from db import get_connection

conn = get_connection()

if conn.is_connected():
    print("Database Connected Successfully!")
else:
    print("Connection Failed")