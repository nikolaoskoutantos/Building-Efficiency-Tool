"""
Mock data initialization for PostgreSQL database.
Updated to work with the new db structure and PostgreSQL.
"""


import os
import psycopg2
from sqlalchemy.orm import Session
from .connection import SessionLocal, engine  # Updated import
from models.knowledge import Knowledge
from models.predictor import Predictor
from models.service import Service
from models.rate import Rate
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

def get_db_url():
    """Get the database URL from environment or raise if not set."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. Please define it in your .env file as DATABASE_URL=postgresql://user:password@host:port/dbname"
        )
    return db_url

def insert_mock_data():
    """
    Main function to insert all mock data into PostgreSQL database.
    """
    db = SessionLocal()
    try:
        print("🔄 Checking and initializing mock data...")

        # Skipping services data insertion
        print("⏩ Skipping services data insertion.")

        # Add a pilot building and three sensors if not already present
        from models.hvac_models import Building
        from models.sensor import Sensor

        if not db.query(Building).filter_by(name="Pilot1").first():
            pilot_building = Building(
                did="0xA",
                name="Pilot1",
                address="Athens, Greece",
                lat="37.99",
                lon="23.73"
            )
            db.add(pilot_building)
            db.commit()
            db.refresh(pilot_building)
            print("🏢 Added building: Pilot1")
        else:
            pilot_building = db.query(Building).filter_by(name="Pilot1").first()
            print("🏢 Building Pilot1 already exists")

        sensors_to_add = [
            {
                "type": "temperature",
                "rate_of_sampling": 5.0,
                "unit": "Celsius",
                "lat": 37.99378878796816,
                "lon": 23.732937037886362,
                "room": "101",
                "zone": "A",
                "central_unit": "CU1"
            },
            {
                "type": "presence",
                "rate_of_sampling": 5.0,
                "unit": "bool",
                "lat": 37.99378878796816,
                "lon": 23.732937037886362,
                "room": "101",
                "zone": "A",
                "central_unit": "CU1"
            },
            {
                "type": "energy",
                "rate_of_sampling": 5.0,
                "unit": "kWh",
                "lat": 37.99378878796816,
                "lon": 23.732937037886362,
                "room": "101",
                "zone": "A",
                "central_unit": "CU1"
            },
        ]

        for sensor_data in sensors_to_add:
            exists = db.query(Sensor).filter_by(
                type=sensor_data["type"],
                lat=sensor_data["lat"],
                lon=sensor_data["lon"],
                unit=sensor_data["unit"],
                room=sensor_data["room"],
                zone=sensor_data["zone"],
                central_unit=sensor_data["central_unit"]
            ).first()
            if not exists:
                sensor = Sensor(
                    building_id=pilot_building.id,
                    hvac_id=None,
                    type=sensor_data["type"],
                    lat=sensor_data["lat"],
                    lon=sensor_data["lon"],
                    rate_of_sampling=sensor_data["rate_of_sampling"],
                    raw_data_id=0,
                    unit=sensor_data["unit"],
                    room=sensor_data["room"],
                    zone=sensor_data["zone"],
                    central_unit=sensor_data["central_unit"]
                )
                db.add(sensor)
                print(f"🌡️ Added sensor: {sensor_data['type']} ({sensor_data['unit']}) in room {sensor_data['room']}, zone {sensor_data['zone']}, central unit {sensor_data['central_unit']}")
            else:
                print(f"🌡️ Sensor {sensor_data['type']} already exists in room {sensor_data['room']}, zone {sensor_data['zone']}, central unit {sensor_data['central_unit']}")
        db.commit()

        # Add mock sensor_data for each sensor (2-3 hours, 5-min intervals)
        from models.sensordata import SensorData
        import datetime
        sensors = db.query(Sensor).filter(Sensor.building_id == pilot_building.id).all()
        now = datetime.datetime.now()
        for sensor in sensors:
            # 2 hours of data, 5-min intervals = 24 points
            for i in range(24):
                timestamp = now - datetime.timedelta(minutes=5 * (24 - i))
                if sensor.type == "temperature":
                    value = round(20 + 5 * (i % 3) + (i % 2), 2)  # Simulate temp
                    measurement_type = "temperature"
                    unit = "celsius"
                elif sensor.type == "presence":
                    value = int(i % 2 == 0)  # Simulate presence
                    measurement_type = "presence"
                    unit = "bool"
                elif sensor.type == "energy":
                    value = round(0.5 + 0.1 * (i % 5), 2)  # Simulate kWh
                    measurement_type = "energy"
                    unit = "kWh"
                else:
                    value = 0
                    measurement_type = "unknown"
                    unit = "unknown"
                sensor_data = SensorData(
                    sensor_id=sensor.id,
                    timestamp=timestamp,
                    value=value,
                    measurement_type=measurement_type,
                    unit=unit
                )
                db.add(sensor_data)
            print(f"📈 Added mock sensor_data for sensor {sensor.type}")
        db.commit()
        sensors_to_add = [
            {
                "type": "presence",
                "rate_of_sampling": 5.0,
                "unit": "bool",
                "lat": 37.99378878796816,
                "lon": 23.732937037886362,
                "room": "101",
                "zone": "A",
                "central_unit": "CU1"
            },
            {
                "type": "energy",
                "rate_of_sampling": 5.0,
                "unit": "kWh",
                "lat": 37.99378878796816,
                "lon": 23.732937037886362,
                "room": "101",
                "zone": "A",
                "central_unit": "CU1"
            },
        ]

        for sensor_data in sensors_to_add:
            exists = db.query(Sensor).filter_by(
                type=sensor_data["type"],
                lat=sensor_data["lat"],
                lon=sensor_data["lon"],
                unit=sensor_data["unit"],
                room=sensor_data["room"],
                zone=sensor_data["zone"],
                central_unit=sensor_data["central_unit"]
            ).first()
            if not exists:
                sensor = Sensor(
                    building_id=pilot_building.id,
                    hvac_id=None,
                    type=sensor_data["type"],
                    lat=sensor_data["lat"],
                    lon=sensor_data["lon"],
                    rate_of_sampling=sensor_data["rate_of_sampling"],
                    raw_data_id=0,
                    unit=sensor_data["unit"],
                    room=sensor_data["room"],
                    zone=sensor_data["zone"],
                    central_unit=sensor_data["central_unit"]
                )
                db.add(sensor)
                print(f"🌡️ Added sensor: {sensor_data['type']} ({sensor_data['unit']}) in room {sensor_data['room']}, zone {sensor_data['zone']}, central unit {sensor_data['central_unit']}")
            else:
                print(f"🌡️ Sensor {sensor_data['type']} already exists in room {sensor_data['room']}, zone {sensor_data['zone']}, central unit {sensor_data['central_unit']}")
        db.commit()
            
        # Add initial knowledge data if not already present
        if not db.query(Knowledge).first():
            print("📝 Initializing knowledge data...")
            insert_knowledge_from_sql()
        else:
            print("✅ Knowledge data already exists")
            
        # Add initial predictor data if not already present  
        if not db.query(Predictor).first():
            print("📝 Initializing predictor data...")
            insert_predictor_from_sql()
        else:
            print("✅ Predictor data already exists")
            
        print("✅ Mock data initialization completed!")
        
    except Exception as e:
        print(f"❌ Error during mock data initialization: {str(e)}")
    finally:
        db.close()

def execute_sql_file(sql_file_name: str):
    """
    Execute a SQL file against the PostgreSQL database.
    """
    try:
        # Get the path to the SQL file in the mock_data folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(current_dir, 'mock_data', sql_file_name)
        
        if not os.path.exists(sql_file_path):
            print(f"❌ SQL file not found at: {sql_file_path}")
            return False
            
        # Parse database URL
        db_url = get_db_url()
        
        # Connect to PostgreSQL and execute SQL
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
                sql_script = sql_file.read()
                
                # Split the script into individual statements
                statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
                
                for statement in statements:
                    if statement:
                        cursor.execute(statement)
                
            conn.commit()
            print(f"✅ Successfully executed {sql_file_name}")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error executing SQL file {sql_file_name}: {str(e)}")
            return False
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"❌ Database connection error for {sql_file_name}: {str(e)}")
        return False

def insert_services_from_sql():
    """Execute the services_data.sql file to populate initial services."""
    return execute_sql_file('services_data.sql')

def insert_knowledge_from_sql():
    """Execute the knowledge_data.sql file to populate initial knowledge assets."""
    return execute_sql_file('knowledge_data.sql')

def insert_predictor_from_sql():
    """Execute the predictor_data.sql file to populate initial predictor models."""
    return execute_sql_file('predictor_data.sql')

def insert_sample_ratings():
    """
    Insert sample encrypted ratings for testing.
    """
    try:
        from db.functions import submit_rating
        
        db = SessionLocal()
        
        # Sample ratings data
        sample_ratings = [
            {"service_id": 1, "wallet": "0x1234567890abcdef1234567890abcdef12345678", "rating": 4.5, "feedback": "Great service!"},
            {"service_id": 1, "wallet": "0xabcdef1234567890abcdef1234567890abcdef12", "rating": 3.8, "feedback": "Good but could be faster"},
            {"service_id": 2, "wallet": "0x9876543210fedcba9876543210fedcba98765432", "rating": 5.0, "feedback": "Excellent accuracy"},
            {"service_id": 2, "wallet": "0x1111222233334444555566667777888899990000", "rating": 4.2, "feedback": "Very reliable"},
            {"service_id": 3, "wallet": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "rating": 3.5, "feedback": "Average performance"},
        ]
        
        for rating_data in sample_ratings:
            try:
                submit_rating(
                    db=db,
                    service_id=rating_data["service_id"],
                    wallet_address=rating_data["wallet"],
                    rating=rating_data["rating"],
                    feedback=rating_data["feedback"]
                )
            except Exception as e:
                print(f"⚠️  Could not insert sample rating: {str(e)}")
                
        db.commit()
        print("✅ Sample ratings inserted successfully")
        
    except Exception as e:
        print(f"❌ Error inserting sample ratings: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()

def clear_all_data():
    """
    Clear all data from tables (useful for testing).
    """
    try:
        db_url = get_db_url()
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Clear tables in correct order (respecting foreign keys)
        tables = ['rates', 'predictors', 'knowledge', 'services', 'sensors']
        
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            
        conn.commit()
        print("✅ All mock data cleared successfully")
        
    except Exception as e:
        print(f"❌ Error clearing data: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # Can be run directly to insert mock data
    print("🚀 Starting mock data insertion...")
    insert_mock_data()

    # Optionally insert sample ratings
    insert_sample_ratings()

    # Install or update the get_building_sensor_weather stored procedure
    print("⚙️ Installing get_building_sensor_weather stored procedure...")
    execute_sql_file("get_building_sensor_weather.sql")
