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