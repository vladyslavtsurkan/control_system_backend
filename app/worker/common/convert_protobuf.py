from loguru import logger
from datetime import datetime, timezone

from app.generated import telemetry_pb2
from app.schemas import TelemetryReading, TelemetryPayload


def convert_protobuf_to_telemetry(batch: bytes) -> list[TelemetryReading] | None:
    """Convert compressed Protobuf bytes into list of TelemetryReading dicts or None if conversion fails"""
    batch_pb = telemetry_pb2.TelemetryBatch()
    try:
        batch_pb.ParseFromString(batch)
    except Exception as e:
        # Log the error and return None to indicate conversion failure
        logger.error("Failed to parse Protobuf batch: {error}", error=str(e))
        return None

    readings: list[TelemetryReading] = []
    for reading in batch_pb.readings:
        # Extract the actual value based on the type specified in the Protobuf message
        val_type = reading.payload.WhichOneof("value")
        if val_type == "float_val":
            actual_value = reading.payload.float_val
        elif val_type == "int_val":
            actual_value = reading.payload.int_val
        elif val_type == "bool_val":
            actual_value = reading.payload.bool_val
        elif val_type == "str_val":
            actual_value = reading.payload.str_val
        else:
            return None

        # Convert the timestamp from milliseconds to a datetime object
        reading_time = datetime.fromtimestamp(reading.time / 1000.0, tz=timezone.utc)

        # Collect the reading into the list of TelemetryReading objects
        readings.append(
            TelemetryReading(
                sensor_id=reading.sensor_id,
                time=reading_time,
                payload=TelemetryPayload(status=reading.payload.status, value=actual_value),
            )
        )

    return readings
