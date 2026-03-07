import os
os.environ["DATABASE_URL"] = "postgresql://qoe_user:qoe_password@localhost:5444/qoe_database"
os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
from hvac_optimizer_service import HVACOptimizerService

def test_model_loading(optimizer):
    """Test MLflow model loading specifically"""
    print(f"\n" + "="*60)
    print("TESTING MLFLOW MODEL LOADING")
    print("="*60)
    
    # Test Linear Regression Model Loading
    print("\n🔍 Testing Linear Regression Model...")
    try:
        lr_success = optimizer._load_linear_regression_model()
        print(f"✅ Linear Regression loaded: {lr_success}")
        print(f"   - A coefficient: {optimizer.a_coefficient}")
        print(f"   - Avg consumption off: {optimizer.avg_consumption_off}")
    except Exception as e:
        print(f"❌ Linear Regression loading failed: {e}")
    
    # Test Random Forest Model Loading  
    print("\n🌲 Testing Random Forest Model...")
    try:
        rf_success = optimizer._load_random_forest_model()
        print(f"✅ Random Forest loaded: {rf_success}")
        print(f"   - RF Model: {type(optimizer.rf_model)}")
        print(f"   - RF Model is None: {optimizer.rf_model is None}")
        if optimizer.rf_model:
            print(f"   - Model features: {optimizer.rf_model.n_features_in_}")
    except Exception as e:
        print(f"❌ Random Forest loading failed: {e}")
    
    # Overall model readiness
    print(f"\n📊 Model Readiness Check:")
    print(f"   - Is model ready: {optimizer._is_model_ready()}")
    print(f"   - A coefficient: {optimizer.a_coefficient}")
    print(f"   - Avg consumption off: {optimizer.avg_consumption_off}")
    print(f"   - RF model loaded: {optimizer.rf_model is not None}")

if __name__ == "__main__":
    # Instantiate optimizer for building 1 with specific time range
    from datetime import datetime
    start_time = datetime.strptime('2026-03-04 04:55:00', '%Y-%m-%d %H:%M:%S')
    end_time = datetime.strptime('2026-03-05 04:55:00', '%Y-%m-%d %H:%M:%S')
    
    print("Initializing HVAC Optimizer Service for Building ID 1...")
    print(f"Time range: {start_time} to {end_time}")
    optimizer = HVACOptimizerService(building_id=1, start_time=start_time, end_time=end_time)
    
    # Test model loading from MLflow
    test_model_loading(optimizer)

    # Test raw data fetching
    print(f"\n" + "="*60)
    print("RAW DATA FROM DATABASE")
    print("="*60)
    
    print(f"✅ Data shape: {optimizer.data.shape}")
    print(f"✅ Latitude: {optimizer.latitude}, Longitude: {optimizer.longitude}")
    print("\n📋 Data columns:")
    for col in optimizer.data.columns:
        print(f"   - {col}")
    
    print(f"\n📊 Raw data sample (first 3 rows):")
    print(optimizer.data.head(3))
    
    print(f"\n🔍 Data summary by sensor type:")
    if 'sensor_type' in optimizer.data.columns:
        for sensor_type in optimizer.data['sensor_type'].unique():
            count = len(optimizer.data[optimizer.data['sensor_type'] == sensor_type])
            print(f"   - {sensor_type}: {count} rows")
    
    # Test data transformation
    print(f"\n" + "="*60)
    print("DATA TRANSFORMATION FOR RANDOM FOREST")
    print("="*60)
    
    try:
        transformed_data = optimizer._transform_data_for_rf()
        print(f"✅ Transformation successful!")
        print(f"   - Original data shape: {optimizer.data.shape}")
        print(f"   - Transformed data shape: {transformed_data.shape}")
        
        if not transformed_data.empty:
            print(f"\n📋 Transformed data columns:")
            for col in transformed_data.columns:
                print(f"   - {col}")
            print(f"\n📊 Transformed data sample:")
            print(transformed_data.head(3))
        else:
            print("⚠️  Transformed data is empty")
            
    except Exception as e:
        print(f"❌ Error in data transformation: {e}")
        import traceback
        traceback.print_exc()
    
    # Test optimization functionality
    print(f"\n" + "="*60)
    print("OPTIMIZATION TESTING")
    print("="*60)
    
    if not optimizer._is_model_ready():
        print("⚠️  Models not ready for optimization testing.")
        print("\n📝 TO REGISTER NOTEBOOK MODELS:")
        print("   HVACOptimizerService.register_notebook_models_to_mlflow(")
        print("       building_id=1,")
        print("       notebook_rf_model_path='../drafts/random_forest_model.pkl',")
        print("       a_coefficient=0.00144072,")  # From notebook
        print("       avg_cons_off=0.38")
        print("   )")
    else:
        print("✅ Models ready! Testing optimization...")
        
        # Test parameters (similar to notebook examples)
        starting_temp = 24.5
        starting_time = "02/03/2026 18:00"
        outdoor_temps = [22.0, 22.5, 22.8, 23.0, 23.2, 23.5, 23.8, 24.0, 24.2, 24.5, 24.8, 25.0, 25.2]
        setpoint = 23.0
        
        try:
            # Test prediction function first
            print(f"\n🔧 Testing prediction function:")
            operation_test = [1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0]  # Mixed operation
            total_cons, temps = optimizer.predict_one_hour(
                operation=operation_test,
                starting_temp=starting_temp,
                starting_time=starting_time,
                outdoor_temps=outdoor_temps,
                setpoint=setpoint
            )
            print(f"   - Energy consumption: {total_cons:.2f}")
            print(f"   - Final temperature: {temps[-1]:.2f}°C")
            print(f"   - Operation: {operation_test}")
            
            # Test normal optimization
            print(f"\n🏠 Testing Normal Conditions Optimization:")
            result = optimizer.get_optimization_recommendation(
                starting_temp=starting_temp,
                starting_time=starting_time,
                outdoor_temps=outdoor_temps,
                setpoint=setpoint,
                is_peak_hours=False
            )
            print(f"   - Recommendation: {result['recommendation_type']}")
            print(f"   - Energy consumption: {result['energy_consumption']:.2f}")
            print(f"   - Savings: {result['savings_percentage']:.1f}%")
            
        except Exception as e:
            print(f"❌ Optimization test failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)
