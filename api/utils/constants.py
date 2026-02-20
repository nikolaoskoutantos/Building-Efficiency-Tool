from enum import Enum

# Sensor type enum
class SensorType(str, Enum):
    TEMPERATURE = "temperature"
    ENERGY = "energy"
    PRESENCE = "presence"

# Function type enum (for on/off or similar states)
class FunctionType(str, Enum):
    ON = "on"
    OFF = "off"

class Role(str, Enum):
    ADMIN = "admin"
    BUILDING_MANAGER = "building_manager"
    OCCUPANT = "occupant"
    DEVICE = "device"