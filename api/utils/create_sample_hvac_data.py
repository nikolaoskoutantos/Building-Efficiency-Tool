"""
Sample HVAC data populator for testing the database-driven HVAC optimization system.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
import math
from sqlalchemy.orm import Session
from db import SessionLocal
from models.sensor import Sensor
from models.sensordata import HVACSensorData

def create_sample_hvac_data(sensor_id: int, days: int = 30):
    """
    Create sample HVAC data for testing the optimization system.
    
    Args:
        sensor_id: ID of the sensor to create data for
        days: Number of days of data to create
    """
    db = SessionLocal()
    
    try:
        # Verify sensor exists
        sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
        if not sensor:
            print(f"Error: Sensor with ID {sensor_id} not found")
            return
        
        print(f"Creating {days} days of HVAC data for sensor {sensor_id}")
        
        # Generate data
        start_time = datetime.now() - timedelta(days=days)
        current_time = start_time
        
        # Initial conditions
        indoor_temp = 22.0  # Start at 22°C
        setpoint = 22.0
        hvac_operation = 0
        
        data_points = []
        
        for i in range(days * 24 * 12):  # 5-minute intervals
            # Simulate outdoor temperature (sinusoidal pattern)
            hour_of_day = current_time.hour + current_time.minute / 60
            day_of_year = current_time.timetuple().tm_yday
            
            # Daily temperature variation
            daily_temp = 20 + 10 * math.sin((hour_of_day - 6) * math.pi / 12)
            # Seasonal variation
            seasonal_temp = 5 * math.sin((day_of_year - 80) * 2 * math.pi / 365)
            # Random noise
            noise = random.uniform(-2, 2)
            
            outdoor_temp = daily_temp + seasonal_temp + noise
            
            # Simulate HVAC operation logic
            if hvac_operation == 0:  # HVAC OFF
                # Temperature drifts towards outdoor temperature
                temp_drift = (outdoor_temp - indoor_temp) * 0.02
                indoor_temp += temp_drift + random.uniform(-0.1, 0.1)
                
                # Turn on HVAC if temperature deviates too much
                if abs(indoor_temp - setpoint) > 2.0:
                    hvac_operation = 1
                    
                energy_consumption = 0.1 + random.uniform(0, 0.1)  # Base consumption
                outlet_temp = None
                inlet_temp = None
                
            else:  # HVAC ON
                # HVAC actively controls temperature
                if indoor_temp < setpoint:
                    # Heating mode
                    indoor_temp += 0.3 + random.uniform(-0.1, 0.1)
                    outlet_temp = 45 + random.uniform(-5, 5)
                    inlet_temp = 25 + random.uniform(-3, 3)
                else:
                    # Cooling mode
                    indoor_temp -= 0.3 + random.uniform(-0.1, 0.1)
                    outlet_temp = 15 + random.uniform(-3, 3)
                    inlet_temp = 25 + random.uniform(-3, 3)
                
                energy_consumption = 2.5 + random.uniform(0, 1.0)  # Higher consumption when on
                
                # Turn off HVAC if temperature is close to setpoint
                if abs(indoor_temp - setpoint) < 0.5:
                    hvac_operation = 0
            
            # Adjust setpoint occasionally (simulate user behavior)
            if random.random() < 0.001:  # 0.1% chance
                setpoint = random.uniform(20, 24)
            
            # Create data point
            data_point = HVACSensorData(
                sensor_id=sensor_id,
                timestamp=current_time,
                indoor_temp=round(indoor_temp, 2),
                outdoor_temp=round(outdoor_temp, 2),
                hvac_operation=hvac_operation,
                energy_consumption=round(energy_consumption, 3),
                setpoint_temp=round(setpoint, 2),
                outlet_temp=round(outlet_temp, 2) if outlet_temp else None,
                inlet_temp=round(inlet_temp, 2) if inlet_temp else None
            )
            
            data_points.append(data_point)
            
            # Move to next time point
            current_time += timedelta(minutes=5)
            
            # Print progress
            if i % 1000 == 0:
                print(f"Generated {i} data points...")
        
        # Batch insert for efficiency
        print(f"Inserting {len(data_points)} data points into database...")
        db.bulk_save_objects(data_points)
        db.commit()
        
        print(f"Successfully created {len(data_points)} HVAC data points for sensor {sensor_id}")
        
        # Print summary statistics
        on_points = len([p for p in data_points if p.hvac_operation == 1])
        off_points = len([p for p in data_points if p.hvac_operation == 0])
        
        print(f"Data summary:")
        print(f"  - HVAC ON: {on_points} points ({on_points/len(data_points)*100:.1f}%)")
        print(f"  - HVAC OFF: {off_points} points ({off_points/len(data_points)*100:.1f}%)")
        print(f"  - Time range: {start_time} to {current_time}")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

def create_sample_sensor(latitude: float, longitude: float) -> int:
    """
    Create a sample sensor for HVAC testing.
    
    Args:
        latitude: Sensor latitude
        longitude: Sensor longitude
        
    Returns:
        int: ID of the created sensor
    """
    db = SessionLocal()
    
    try:
        sensor = Sensor(
            lat=latitude,
            lon=longitude,
            rate_of_sampling=12.0,  # 5-minute intervals = 12 per hour
            raw_data_id=1,
            unit='celsius'
        )
        
        db.add(sensor)
        db.commit()
        
        print(f"Created sensor with ID {sensor.id} at location ({latitude}, {longitude})")
        return sensor.id
        
    except Exception as e:
        print(f"Error creating sensor: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    # Create sample sensor and data
    latitude = 40.7128  # New York City
    longitude = -74.0060
    
    print("Creating sample HVAC sensor and data...")
    
    # Create sensor
    sensor_id = create_sample_sensor(latitude, longitude)
    
    # Create 30 days of sample data
    create_sample_hvac_data(sensor_id, days=30)
    
    print(f"Sample data creation complete!")
    print(f"You can now train the HVAC model using:")
    print(f"  POST /predict/hvac/train")
    print(f"  Body: {{\"latitude\": {latitude}, \"longitude\": {longitude}, \"sensor_id\": {sensor_id}, \"days_back\": 30}}")
