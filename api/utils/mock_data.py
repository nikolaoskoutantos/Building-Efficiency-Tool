from db import SessionLocal, engine
from models.knowledge import Knowledge
from models.predictor import Predictor
from models.service import Service
import os
import sqlite3
# Import other models as needed

def insert_mock_data():
    db = SessionLocal()
    try:
        # Add initial knowledge data if not already present
        # if not db.query(Knowledge).first():
        #     print("Initializing knowledge data from SQL file...")
        #     insert_knowledge_from_sql()
            
        # # Add initial predictor data if not already present  
        # if not db.query(Predictor).first():
        #     print("Initializing predictor data from SQL file...")
        #     insert_predictor_from_sql()
        
        # Add initial services data if not already present
        if not db.query(Service).first():
            print("Initializing services data from SQL file...")
            insert_services_from_sql()
            
        # Add more mock data for other models as needed
    finally:
        db.close()

def insert_services_from_sql():
    """
    Execute the services_data.sql file to populate initial services
    """
    try:
        # Get the path to the SQL file in the mock_data folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(os.path.dirname(current_dir), 'mock_data', 'services_data.sql')
        
        if os.path.exists(sql_file_path):
            # Get database file path
            db_file_path = os.path.join(os.path.dirname(current_dir), 'dev.db')
            
            # Execute SQL file
            with sqlite3.connect(db_file_path) as conn:
                with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
                    sql_script = sql_file.read()
                    conn.executescript(sql_script)
                conn.commit()
            
            print(f"Successfully executed services_data.sql")
        else:
            print(f"SQL file not found at: {sql_file_path}")
            
    except Exception as e:
        print(f"Error executing services SQL file: {str(e)}")

def insert_knowledge_from_sql():
    """
    Execute the knowledge_data.sql file to populate initial knowledge assets
    """
    try:
        # Get the path to the SQL file in the mock_data folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(os.path.dirname(current_dir), 'mock_data', 'knowledge_data.sql')
        
        if os.path.exists(sql_file_path):
            # Get database file path
            db_file_path = os.path.join(os.path.dirname(current_dir), 'dev.db')
            
            # Execute SQL file
            with sqlite3.connect(db_file_path) as conn:
                with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
                    sql_script = sql_file.read()
                    conn.executescript(sql_script)
                conn.commit()
            
            print(f"Successfully executed knowledge_data.sql")
        else:
            print(f"Knowledge SQL file not found at: {sql_file_path}")
            
    except Exception as e:
        print(f"Error executing knowledge SQL file: {str(e)}")

def insert_predictor_from_sql():
    """
    Execute the predictor_data.sql file to populate initial predictor models
    """
    try:
        # Get the path to the SQL file in the mock_data folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(os.path.dirname(current_dir), 'mock_data', 'predictor_data.sql')
        
        if os.path.exists(sql_file_path):
            # Get database file path
            db_file_path = os.path.join(os.path.dirname(current_dir), 'dev.db')
            
            # Execute SQL file
            with sqlite3.connect(db_file_path) as conn:
                with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
                    sql_script = sql_file.read()
                    conn.executescript(sql_script)
                conn.commit()
            
            print(f"Successfully executed predictor_data.sql")
        else:
            print(f"Predictor SQL file not found at: {sql_file_path}")
            
    except Exception as e:
        print(f"Error executing predictor SQL file: {str(e)}")
