from sqlalchemy import Column, Integer, String, Boolean
from db.connection import Base

class MQTTBrokerConfig(Base):
    __tablename__ = "mqtt_broker_config"

    id = Column(Integer, primary_key=True, index=True)
    broker_url = Column(String, nullable=False, default="localhost")
    broker_port = Column(Integer, nullable=False, default=1883)
    broker_username = Column(String, nullable=True)
    broker_password = Column(String, nullable=True)
    use_tls = Column(Boolean, nullable=False, default=False)
    client_id_prefix = Column(String, nullable=False, default="qoe_device")
    topic_prefix = Column(String, nullable=False, default="qoe")
    keepalive_seconds = Column(Integer, nullable=False, default=60)
    is_active = Column(Boolean, nullable=False, default=True)