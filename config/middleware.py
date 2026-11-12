from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Applies defense-in-depth HTTP security headers across all responses:
    - Content-Security-Policy (tailored to permit official fonts/CDNs & WhatsApp checkout)
    - Permissions-Policy
    - Referrer-Policy
    - X-Content-Type-Options
    - Cache-Control: no-store on sensitive admin/checkout paths
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self' https://wa.me https://api.whatsapp.com;"
        )

    def __call__(self, request):
        response = self.get_response(request)

        # Standard defense headers
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=()')

        # Enforce strict frame denial unless overridden
        if not response.has_header('X-Frame-Options'):
            response['X-Frame-Options'] = 'DENY'

        # Content-Security-Policy
        if not response.has_header('Content-Security-Policy'):
            response['Content-Security-Policy'] = self.csp_policy

        # Prevent caching of authenticated admin dashboard and order/checkout data
        path = request.path or ''
        if path.startswith('/dashboard/') or path.startswith('/admin/') or path.startswith('/orders/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'

        return response

