from django.urls import path
from .views import cron_sheet_cleaner, function_tester, index, my_cron_view, save_facebook_chat, chat_test_page

urlpatterns = [
    path('', index, name='index'),  # Add this line for the index page
    path('webhook/', save_facebook_chat, name='save_facebook_chat'),
    path('cron-job/', my_cron_view, name='my_cron_view'),
    path('cron-sheet-cleaner/', cron_sheet_cleaner, name='cron_sheet_cleaner'),
    path('test-chat/', chat_test_page, name='test_chat_page'),
    path('functest/', function_tester, name='function_tester'),
]