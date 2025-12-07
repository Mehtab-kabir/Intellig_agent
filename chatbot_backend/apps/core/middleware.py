"""
Custom middleware for the application.
"""
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware for logging all HTTP requests with timing information.
    
    Adds a unique request ID to each request for tracing.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000
        
        # Log request details
        logger.info(
            f"[{request_id}] {request.method} {request.path} "
            f"- {response.status_code} - {duration:.2f}ms",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': duration,
            }
        )
        
        # Add request ID to response headers
        response['X-Request-ID'] = request_id
        
        return response
