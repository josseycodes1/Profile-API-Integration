import time
import logging

logger = logging.getLogger(__name__)

class RequestAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()

        response = self.get_response(request)

        duration = time.time() - start

        logger.info(
            f"{request.method} {request.path} "
            f"user={getattr(request.user, 'id', None)} "
            f"status={response.status_code} "
            f"time={round(duration, 3)}s"
        )

        return response
    
    
class DynamicCORSMiddleware:
    """
    Echoes the request Origin back as Access-Control-Allow-Origin.
    This allows credentials (cookies) to work with any origin,
    since browsers reject wildcard + credentials.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get("HTTP_ORIGIN")
        response = self.get_response(request)

        if origin:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Vary"] = "Origin"

        return response

    def process_response(self, request, response):
        return response