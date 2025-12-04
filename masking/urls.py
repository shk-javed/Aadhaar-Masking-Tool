from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_image, name='upload_image'),
    path('preview/<str:filename>/', views.preview_pdf, name='preview_pdf'),
]
