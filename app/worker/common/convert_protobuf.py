from uuid import UUID
from collections import defaultdict

from loguru import logger
from datetime import datetime, timezone

from app.worker.generated import telemetry_pb2
from app.worker.schemas import TelemetryReading


def convert_protobuf_to_telemetry(batch: bytes) -> dict[UUID, list[TelemetryReading]] | None:
    """Convert compressed Protobuf bytes into dict with sensor_id keys and list of TelemetryReading values."""
    batch_pb = telemetry_pb2.TelemetryBatch()
    try:
        batch_pb.ParseFromString(batch)
    except Exception as e:
        # Log the error and return None to indicate conversion failure
        logger.error("Failed to parse Protobuf batch: {error}", error=str(e))
        return None

    telemetry_by_sensor_map = defaultdict(list)
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
            logger.warning("Unknown value type: {value}", value=reading.payload.value)
            continue

        # Convert the timestamp from milliseconds to a datetime object
        reading_time = datetime.fromtimestamp(reading.time / 1000.0, tz=timezone.utc)

        try:
            sensor_id = UUID(reading.sensor_id)
        except ValueError:
            logger.error("Failed to parse sensor_id: {sensor_id}", sensor_id=reading.sensor_id)
            continue

        telemetry_by_sensor_map[sensor_id].append(
            {
                "sensor_id": sensor_id,
                "time": reading_time,
                "payload": {
                    "value": actual_value,
                    "status": reading.payload.status,
                },
            }
        )

    return telemetry_by_sensor_map
