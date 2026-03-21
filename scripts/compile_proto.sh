#!/bin/bash
# Create the output directory if it doesn't exist
mkdir -p app/worker/generated
touch app/worker/generated/__init__.py

# Generate Python classes from the telemetry.proto file
python -m grpc_tools.protoc \
    -I contracts \
    --python_out=app/worker/generated \
    contracts/telemetry.proto

echo "Protobuf classes generated successfully in app/worker/generated/ directory."
