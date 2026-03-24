# XADRAS - Camera & Stream Views
# Implementation of Camera/Stream API endpoints

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import logging

from .models import Camera, Stream, CameraHealthLog
from .serializers import (
    CameraSerializer, CameraCreateSerializer, StreamSerializer,
    StreamAttachSerializer, CameraHealthLogSerializer, CameraTestSerializer,
    CameraCalibrationSerializer, CameraStatusSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)

class CameraViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Camera management
    Supports CRUD operations and camera-specific actions
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter cameras based on user permissions"""
        user = self.request.user
        
        # Users can see cameras they created or all cameras if they're staff
        if user.is_staff:
            return Camera.objects.all()
        else:
            return Camera.objects.filter(created_by=user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CameraCreateSerializer
        return CameraSerializer
    
    @method_decorator(ratelimit(key='user', rate='2/m', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        """Create a new camera"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        camera = serializer.save()
        
        # Perform initial health check
        try:
            camera.health_check()
        except Exception as e:
            logger.warning(f"Initial health check failed for camera {camera.name}: {e}")
        
        logger.info(f"Camera created: {camera.name} by {request.user.username}")
        
        response_serializer = CameraSerializer(camera, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test camera connection"""
        camera = self.get_object()
        
        try:
            is_healthy, response_time, error_message = camera.test_connection()
            
            return Response({
                'camera_id': camera.id,
                'name': camera.name,
                'is_healthy': is_healthy,
                'status': camera.status,
                'response_time': response_time,
                'error_message': error_message or '',
                'tested_at': timezone.now()
            })
            
        except Exception as e:
            logger.error(f"Camera test failed for {camera.name}: {e}")
            return Response(
                {'error': f'Camera test failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def health(self, request, pk=None):
        """Get camera health status and recent logs"""
        camera = self.get_object()
        
        # Get recent health logs
        recent_logs = camera.health_logs.all()[:10]
        
        # Perform fresh health check
        try:
            is_healthy, response_time, error_message = camera.health_check()
        except Exception as e:
            is_healthy = False
            response_time = 0
            error_message = str(e)
        
        return Response({
            'camera': CameraStatusSerializer({
                'id': camera.id,
                'name': camera.name,
                'location': camera.location,
                'status': camera.status,
                'is_online': camera.is_online,
                'last_health_check': camera.last_health_check,
                'is_calibrated': camera.is_calibrated,
                'current_stream': camera.current_stream,
                'response_time': response_time,
                'error_message': error_message or ''
            }).data,
            'recent_logs': CameraHealthLogSerializer(recent_logs, many=True).data
        })
    
    @action(detail=True, methods=['post'])
    def calibrate(self, request, pk=None):
        """Start or update camera calibration"""
        camera = self.get_object()
        
        if not camera.is_online:
            return Response(
                {'error': 'Camera must be online to calibrate'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CameraCalibrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update calibration data
        camera.calibration_data = serializer.validated_data['calibration_data']
        camera.is_calibrated = True
        camera.status = Camera.ONLINE  # Reset from CALIBRATING if it was set
        camera.save()
        
        logger.info(f"Camera calibrated: {camera.name}")
        
        return Response({
            'message': 'Camera calibration updated successfully',
            'camera_id': camera.id,
            'is_calibrated': camera.is_calibrated,
            'calibration_data': camera.calibration_data
        })
    
    @action(detail=True, methods=['get'])
    def calibration(self, request, pk=None):
        """Get camera calibration status and data"""
        camera = self.get_object()
        
        return Response({
            'camera_id': camera.id,
            'name': camera.name,
            'is_calibrated': camera.is_calibrated,
            'calibration_data': camera.calibration_data,
            'status': camera.status
        })
    
    @action(detail=False, methods=['get'])
    def status_overview(self, request):
        """Get overview of all camera statuses"""
        cameras = self.get_queryset()
        
        status_counts = {
            'total': cameras.count(),
            'online': cameras.filter(status=Camera.ONLINE).count(),
            'offline': cameras.filter(status=Camera.OFFLINE).count(),
            'error': cameras.filter(status=Camera.ERROR).count(),
            'calibrated': cameras.filter(is_calibrated=True).count(),
            'active_streams': Stream.objects.filter(is_active=True, camera__in=cameras).count()
        }
        
        # Get cameras by status
        cameras_by_status = {}
        for status_choice in Camera.STATUS_CHOICES:
            status_key = status_choice[0]
            cameras_by_status[status_key] = CameraSerializer(
                cameras.filter(status=status_key),
                many=True,
                context={'request': request}
            ).data
        
        return Response({
            'overview': status_counts,
            'cameras_by_status': cameras_by_status
        })


class StreamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Stream management
    """
    serializer_class = StreamSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter streams based on user permissions"""
        user = self.request.user
        
        if user.is_staff:
            return Stream.objects.all()
        else:
            # Users can see streams from cameras they created
            return Stream.objects.filter(camera__created_by=user)
    
    @action(detail=False, methods=['post'])
    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def attach(self, request):
        """Attach camera to game (start streaming)"""
        serializer = StreamAttachSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        camera_id = serializer.validated_data['camera_id']
        game_id = serializer.validated_data['game_id']
        quality_settings = serializer.validated_data.get('quality_settings', {})
        recording_enabled = serializer.validated_data.get('recording_enabled', False)
        
        try:
            with transaction.atomic():
                # Get camera and game
                camera = Camera.objects.get(id=camera_id)
                from game.models import Game
                game = Game.objects.get(id=game_id)
                
                # Create stream
                stream = Stream.objects.create(
                    camera=camera,
                    game=game,
                    quality_settings=quality_settings,
                    recording_enabled=recording_enabled
                )
                
                # Start the stream
                stream.start_stream()
                
                logger.info(f"Stream attached: Camera {camera.name} to Game {game.id}")
                
                return Response(
                    StreamSerializer(stream, context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"Failed to attach stream: {e}")
            return Response(
                {'error': f'Failed to attach stream: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['delete'])
    def detach(self, request, pk=None):
        """Detach stream (stop streaming)"""
        stream = self.get_object()
        
        if not stream.is_active:
            return Response(
                {'error': 'Stream is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Stop the stream
        stream.stop_stream()
        
        logger.info(f"Stream detached: {stream.id}")
        
        return Response({
            'message': 'Stream detached successfully',
            'stream_id': stream.id,
            'stopped_at': stream.ended_at
        })
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get stream status"""
        stream = self.get_object()
        
        return Response(stream.get_status())
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active streams"""
        active_streams = self.get_queryset().filter(is_active=True)
        
        serializer = StreamSerializer(active_streams, many=True, context={'request': request})
        return Response(serializer.data)


class CameraHealthLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Camera Health Logs (read-only)
    """
    serializer_class = CameraHealthLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter health logs based on user permissions"""
        user = self.request.user
        
        if user.is_staff:
            return CameraHealthLog.objects.all()
        else:
            # Users can see logs from cameras they created
            return CameraHealthLog.objects.filter(camera__created_by=user)
