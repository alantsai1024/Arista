#!/bin/bash
# MQTT topic subscription script for testing

MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USERNAME="${MQTT_USERNAME:-}"
MQTT_PASSWORD="${MQTT_PASSWORD:-}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    echo "Usage: $0 [state|telemetry|all|device_id]"
    echo ""
    echo "Subscribe to MQTT topics for testing:"
    echo "  state       - Subscribe to all device state topics (retained)"
    echo "  telemetry   - Subscribe to all telemetry topics (not retained)"
    echo "  all         - Subscribe to all topics"
    echo "  <device_id> - Subscribe to specific device topics"
    echo ""
    echo "Environment variables:"
    echo "  MQTT_HOST     - MQTT broker host (default: localhost)"
    echo "  MQTT_PORT     - MQTT broker port (default: 1883)"
    echo "  MQTT_USERNAME - MQTT username (optional)"
    echo "  MQTT_PASSWORD - MQTT password (optional)"
    echo ""
    echo "Examples:"
    echo "  $0 state"
    echo "  $0 telemetry"
    echo "  $0 all"
    echo "  $0 550e8400-e29b-41d4-a716-446655440000"
}

build_auth_args() {
    AUTH_ARGS=""
    if [ -n "$MQTT_USERNAME" ] && [ -n "$MQTT_PASSWORD" ]; then
        AUTH_ARGS="-u $MQTT_USERNAME -P $MQTT_PASSWORD"
    fi
    echo "$AUTH_ARGS"
}

subscribe_state() {
    echo -e "${BLUE}Subscribing to state topics (retained messages)...${NC}"
    echo -e "${YELLOW}Topic: arista/default/+/state${NC}"
    echo -e "${GREEN}You should immediately receive retained state messages${NC}"
    echo ""
    
    AUTH_ARGS=$(build_auth_args)
    mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" $AUTH_ARGS \
        -t "arista/default/+/state" \
        -v \
        -q 1
}

subscribe_telemetry() {
    echo -e "${BLUE}Subscribing to telemetry topics (non-retained messages)...${NC}"
    echo -e "${YELLOW}Topic: arista/default/+/telemetry/+${NC}"
    echo -e "${GREEN}You will only receive NEW messages after subscription${NC}"
    echo ""
    
    AUTH_ARGS=$(build_auth_args)
    mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" $AUTH_ARGS \
        -t "arista/default/+/telemetry/+" \
        -v \
        -q 1
}

subscribe_all() {
    echo -e "${BLUE}Subscribing to all topics...${NC}"
    echo -e "${YELLOW}Topics: arista/default/+#${NC}"
    echo ""
    
    AUTH_ARGS=$(build_auth_args)
    mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" $AUTH_ARGS \
        -t "arista/default/+#" \
        -v \
        -q 1
}

subscribe_device() {
    DEVICE_ID=$1
    echo -e "${BLUE}Subscribing to device: $DEVICE_ID${NC}"
    echo -e "${YELLOW}Topics:${NC}"
    echo "  - arista/default/$DEVICE_ID/state"
    echo "  - arista/default/$DEVICE_ID/telemetry/+"
    echo ""
    
    AUTH_ARGS=$(build_auth_args)
    mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" $AUTH_ARGS \
        -t "arista/default/$DEVICE_ID/state" \
        -t "arista/default/$DEVICE_ID/telemetry/+" \
        -v \
        -q 1
}

# Check if mosquitto_sub is available
if ! command -v mosquitto_sub &> /dev/null; then
    echo "Error: mosquitto_sub not found"
    echo "Install mosquitto-clients:"
    echo "  Ubuntu/Debian: sudo apt-get install mosquitto-clients"
    echo "  macOS: brew install mosquitto"
    echo "  Or use Docker: docker compose exec mqtt mosquitto_sub ..."
    exit 1
fi

# Parse arguments
case "$1" in
    state)
        subscribe_state
        ;;
    telemetry)
        subscribe_telemetry
        ;;
    all)
        subscribe_all
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        echo "Error: No topic specified"
        echo ""
        show_help
        exit 1
        ;;
    *)
        # Assume it's a device ID
        subscribe_device "$1"
        ;;
esac
