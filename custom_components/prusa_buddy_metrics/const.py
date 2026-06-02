DOMAIN = "prusa_buddy_metrics"

CONF_UDP_PORT = "udp_port"

DEFAULT_UDP_PORT = 8514
UNAVAILABLE_TIMEOUT = 300  # seconds (5 minutes)

# Sensor classification rules: (keywords, device_class, unit, is_binary, state_class)
# Matched against "<measurement>_<field>" lowercased. First match wins.
# state_class: "measurement", "total_increasing", or None
SENSOR_RULES = [
    (["temp"],                  "temperature",  "°C",   False, "measurement"),
    (["voltage"],               "voltage",      "V",    False, "measurement"),
    (["current"],               "current",      "A",    False, "measurement"),
    (["xbe_fan"],               None,           "rpm",  False, "measurement"),
    (["pwm"],                   "power_factor", "%",    False, "measurement"),
    (["heap", "free", "total"], None,           "B",    False, "measurement"),
    (["recv", "sent", "bytes"], None,           "B",    False, "total_increasing"),
    (["usage"],                 None,           "%",    False, "measurement"),
    (["state"],                 None,           None,   True,  None),
    (["enabled"],               None,           None,   True,  None),
    (["stall"],                 None,           None,   True,  None),
]
