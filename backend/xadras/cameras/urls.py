# XADRAS - Camera & Stream URLs
# URL routing for camera and stream endpoints

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CameraViewSet, StreamViewSet, CameraHealthLogViewSet

# Create router for camera/stream endpoints
router = DefaultRouter()
router.register(r'cameras', CameraViewSet, basename='camera')
router.register(r'streams', StreamViewSet, basename='stream')
router.register(r'camera-health', CameraHealthLogViewSet, basename='camera-health')

urlpatterns = [
    path('', include(router.urls)),
]
