from sqlalchemy import BigInteger, Column, Float, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from db.connection import Base

AGGREGATION_MEAN = "mean"
AGGREGATION_SUM = "sum"
AGGREGATION_MIN = "min"
AGGREGATION_MAX = "max"
AGGREGATION_LAST = "last"
AGGREGATION_MAJORITY = "majority"


class SensorUnit(Base):
    """
    Canonical unit registry. Each row defines one unit with:
      - symbol       : the canonical string stored on Sensor.unit and used in responses
                       (e.g. "°C", "W", "kWh", "%")
      - quantity     : physical quantity group (temperature, power, energy, …)
      - display_name : human-readable label shown in UI
      - aliases      : JSONB list of alternate spellings/abbreviations that are
                       normalised to this unit on write (e.g. ["celsius", "degC"])
      - si_symbol    : SI unit for this quantity (used for inter-unit conversion context)
      - conversion_factor : multiply raw value by this to reach si_symbol.
                            NULL for non-linear conversions (e.g. °C→K).
      - aggregation_method : default bucket aggregation for sensors using this unit
                             (e.g. mean, sum, min, max, last, majority).
    """

    __tablename__ = "sensor_units"

    id = Column(BigInteger, primary_key=True)
    symbol = Column(Text, nullable=False)           # canonical, shown to users
    quantity = Column(Text, nullable=False)         # grouping key
    display_name = Column(Text, nullable=False)
    aliases = Column(JSONB, nullable=False, default=list)  # list[str], all lowercase
    si_symbol = Column(Text, nullable=True)
    conversion_factor = Column(Float, nullable=True)  # raw × factor = SI value
    aggregation_method = Column(Text, nullable=False, default=AGGREGATION_MEAN)

    __table_args__ = (
        UniqueConstraint("symbol", name="uq_sensor_units_symbol"),
    )
