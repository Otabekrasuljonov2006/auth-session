class DebugRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("\n=== REQUEST KIRDI ===")
        print("Path:", request.path)
        print("User:", request.user)
        print("Authenticated:", request.user.is_authenticated)
        print("Session key:", request.session.session_key)

        response = self.get_response(request)

        print("=== RESPONSE QAYTDI ===")
        print("Status:", response.status_code)

        return response
