from django.urls import path
from .views import index, save_facebook_chat, chat_test_page

urlpatterns = [
    path('', index, name='index'),  # Add this line for the index page
    path('webhook/', save_facebook_chat, name='save_facebook_chat'),
    path('test-chat/', chat_test_page, name='test_chat_page'),
]