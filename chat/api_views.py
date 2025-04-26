from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Chat, UserProfile

class ChatHistoryAPIView(APIView):
    #authentication_classes = [JWTAuthentication]
    #permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id query param required'}, status=400)

        try:
            user_profile = UserProfile.objects.get(facebook_id=user_id)
        except UserProfile.DoesNotExist:
            return Response({'error': 'UserProfile not found'}, status=404)

        chats = Chat.objects.filter(user=user_profile).order_by('-timestamp')[:6]
        history = [{
            'message': c.message,
            'reply': c.reply,
            'timestamp': c.timestamp.isoformat()
        } for c in reversed(chats)]

        return Response({'history': history})