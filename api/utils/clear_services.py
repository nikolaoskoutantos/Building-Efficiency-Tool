#!/usr/bin/env python3
"""
Script to clear/truncate the services table
"""
import sqlite3
import os

def clear_services_table():
    try:
        # Get database file path
        db_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dev.db')
        
        if not os.path.exists(db_file_path):
            print(f"Database file not found at: {db_file_path}")
            return
        
        # Connect and clear services table
        with sqlite3.connect(db_file_path) as conn:
            cursor = conn.cursor()
            
            # Check if services table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services';")
            if cursor.fetchone():
                # Clear all services
                cursor.execute("DELETE FROM services;")
                
                # Reset auto-increment if sqlite_sequence exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence';")
                if cursor.fetchone():
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='services';")
                
                # Vacuum to reclaim space
                cursor.execute("VACUUM;")
                
                conn.commit()
                print("✅ Services table cleared successfully!")
                
                # Show count to verify
                cursor.execute("SELECT COUNT(*) FROM services;")
                count = cursor.fetchone()[0]
                print(f"Services count after clearing: {count}")
            else:
                print("❌ Services table does not exist!")
                
    except Exception as e:
        print(f"❌ Error clearing services table: {str(e)}")

if __name__ == "__main__":
    clear_services_table()
