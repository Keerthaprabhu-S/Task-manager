from rest_framework.views import exception_handler

def api_exception_handler(exc, context):
    """Consistent error envelope: {"error": {"status", "message", "details"}}."""
    resp = exception_handler(exc, context)
    if resp is None:
        return None
    data = resp.data
    if isinstance(data, dict) and "detail" in data:
        message = str(data["detail"])
    else:
        message = "Validation failed" if resp.status_code == 400 else "Request failed"
    resp.data = {"error": {"status": resp.status_code, "message": message,
                           "details": data if resp.status_code == 400 else None}}
    return resp
