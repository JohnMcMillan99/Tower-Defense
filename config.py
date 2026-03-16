"""
Shared configuration for Tower Defense 3.
"""

# Set to True to enable debug logging to debug.log (useful for troubleshooting)
DEBUG = False


def log_debug(msg, data=None, location="main"):
    """Write debug log entry only when DEBUG is True."""
    if not DEBUG:
        return
    import json
    import time
    log_entry = {
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": msg,
        "data": data or {},
    }
    try:
        with open("debug.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
