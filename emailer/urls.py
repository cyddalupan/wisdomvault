from django.urls import path
from . import admin

app_name = 'emailer'

urlpatterns = [
    path('admin/', admin.site.urls),
]