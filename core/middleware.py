"""
Güvenlik başlıkları (docs/callender.md bölüm 12.8), ek paket olmadan.
CSP satır içi script ve stile izin vermez; JS dosyaları static/js altında, stiller sınıflarla verilir.
"""

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; script-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=()"


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        return response
