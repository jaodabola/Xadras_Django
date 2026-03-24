# XADRAS - Camera & Stream Models
# Implementation based on Stream AI specifications
# Priority: CRITICAL - Required by Vision AI, Stream AI, Tournament AI

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import URLValidator, MinValueValidator, MaxValueValidator
import uuid
import json

User = get_user_model()

class Camera(models.Model):
    """
    Camera model for managing physical and IP cameras
    Based on Stream AI specifications
    """
    # Camera Types
    USB = 'USB'
    IP = 'IP'
    RTSP = 'RTSP'
    HTTP = 'HTTP'
    
    CAMERA_TYPE_CHOICES = [
        (USB, 'USB Camera'),
        (IP, 'IP Camera'),
        (RTSP, 'RTSP Camera'),
        (HTTP, 'HTTP Camera'),
    ]
    
    # Camera Status
    ONLINE = 'ONLINE'
    OFFLINE = 'OFFLINE'
    ERROR = 'ERROR'
    CALIBRATING = 'CALIBRATING'
    MAINTENANCE = 'MAINTENANCE'
    
    STATUS_CHOICES = [
        (ONLINE, 'Online'),
        (OFFLINE, 'Offline'),
        (ERROR, 'Error'),
        (CALIBRATING, 'Calibrating'),
        (MAINTENANCE, 'Maintenance'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Camera display name")
    description = models.TextField(blank=True, help_text="Camera description")
    
    # Camera Configuration
    camera_type = models.CharField(max_length=10, choices=CAMERA_TYPE_CHOICES)
    connection_url = models.URLField(
        max_length=500,
        help_text="Camera connection URL (e.g., rtsp://user:pass@192.168.1.100:554/stream)"
    )
    
    # Network Configuration
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        help_text="Camera IP address"
    )
    port = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text="Camera port number"
    )
    
    # Authentication
    username = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Camera authentication username"
    )
    password = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Camera authentication password"
    )
    
    # Physical Location
    location = models.CharField(
        max_length=200,
        help_text="Physical location description (e.g., 'Board 1', 'Table A')"
    )
    
    # Status and Health
    is_active = models.BooleanField(
        default=True,
        help_text="Camera is active and available for use"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default=OFFLINE
    )
    last_health_check = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last successful health check"
    )
    
    # Vision AI Integration
    calibration_data = models.JSONField(
        default=dict,
        help_text="Camera calibration data from Vision AI"
    )
    is_calibrated = models.BooleanField(
        default=False,
        help_text="Camera has been calibrated by Vision AI"
    )
    
    # Management
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="User who registered this camera"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['location', 'name']
        verbose_name = 'Camera'
        verbose_name_plural = 'Cameras'
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['location']),
            models.Index(fields=['camera_type']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.location})"
    
    def save(self, *args, **kwargs):
        # Extract IP address from connection URL if not provided
        if not self.ip_address and self.connection_url:
            self._extract_ip_from_url()
        super().save(*args, **kwargs)
    
    def _extract_ip_from_url(self):
        """Extract IP address from connection URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.connection_url)
            if parsed.hostname:
                self.ip_address = parsed.hostname
                if parsed.port:
                    self.port = parsed.port
        except Exception:
            pass  # Keep existing values if parsing fails
    
    def health_check(self):
        """
        Perform health check on camera
        Returns (is_healthy: bool, response_time: float, error_message: str)
        """
        import time
        import requests
        from urllib.parse import urlparse
        
        start_time = time.time()
        
        try:
            if self.camera_type == self.USB:
                # For USB cameras, we'd need to check if device exists
                # This is a simplified check
                is_healthy = True
                error_message = None
                
            elif self.camera_type in [self.IP, self.HTTP]:
                # HTTP-based camera check
                response = requests.head(
                    self.connection_url,
                    timeout=5,
                    auth=(self.username, self.password) if self.username else None
                )
                is_healthy = response.status_code < 400
                error_message = None if is_healthy else f"HTTP {response.status_code}"
                
            elif self.camera_type == self.RTSP:
                # RTSP camera check (simplified - would need proper RTSP client)
                # For now, just check if we can resolve the hostname
                parsed = urlparse(self.connection_url)
                if parsed.hostname:
                    import socket
                    socket.gethostbyname(parsed.hostname)
                    is_healthy = True
                    error_message = None
                else:
                    is_healthy = False
                    error_message = "Invalid RTSP URL"
            
            else:
                is_healthy = False
                error_message = "Unsupported camera type"
                
        except Exception as e:
            is_healthy = False
            error_message = str(e)
        
        response_time = time.time() - start_time
        
        # Update camera status
        if is_healthy:
            self.status = self.ONLINE
            self.last_health_check = timezone.now()
        else:
            self.status = self.ERROR
        
        self.save()
        
        # Log health check result
        CameraHealthLog.objects.create(
            camera=self,
            status=self.status,
            response_time=response_time,
            error_message=error_message or ""
        )
        
        return is_healthy, response_time, error_message
    
    def get_stream_url(self):
        """Get the stream URL for this camera"""
        return self.connection_url
    
    def test_connection(self):
        """Test camera connection (alias for health_check)"""
        return self.health_check()
    
    @property
    def is_online(self):
        """Check if camera is currently online"""
        return self.status == self.ONLINE and self.is_active
    
    @property
    def current_stream(self):
        """Get currently active stream for this camera"""
        return self.streams.filter(is_active=True).first()


class Stream(models.Model):
    """
    Stream model for associating cameras with games
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        related_name='streams',
        help_text="Camera providing the stream"
    )
    game = models.ForeignKey(
        'game.Game',
        on_delete=models.CASCADE,
        related_name='streams',
        help_text="Game being streamed"
    )
    
    # Stream Status
    is_active = models.BooleanField(
        default=False,
        help_text="Stream is currently active"
    )
    
    # Timing
    started_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When stream was started"
    )
    ended_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When stream was ended"
    )
    
    # Stream Configuration
    quality_settings = models.JSONField(
        default=dict,
        help_text="Stream quality settings (resolution, fps, etc.)"
    )
    
    # Recording (optional)
    recording_enabled = models.BooleanField(
        default=False,
        help_text="Enable recording of this stream"
    )
    recording_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path to recorded file (if recording enabled)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stream'
        verbose_name_plural = 'Streams'
        indexes = [
            models.Index(fields=['camera', 'is_active']),
            models.Index(fields=['game']),
            models.Index(fields=['is_active']),
        ]
        # Ensure only one active stream per camera
        constraints = [
            models.UniqueConstraint(
                fields=['camera'],
                condition=models.Q(is_active=True),
                name='unique_active_stream_per_camera'
            )
        ]
    
    def __str__(self):
        return f"Stream: {self.camera.name} -> Game {self.game.id}"
    
    def start_stream(self):
        """Start the stream"""
        if not self.camera.is_online:
            raise ValueError("Camera is not online")
        
        # End any existing active streams for this camera
        Stream.objects.filter(camera=self.camera, is_active=True).update(
            is_active=False,
            ended_at=timezone.now()
        )
        
        self.is_active = True
        self.started_at = timezone.now()
        self.ended_at = None
        self.save()
        
        # Set default quality settings if not provided
        if not self.quality_settings:
            self.quality_settings = {
                'resolution': '1280x720',
                'fps': 30,
                'format': 'MJPEG'
            }
            self.save()
    
    def stop_stream(self):
        """Stop the stream"""
        self.is_active = False
        self.ended_at = timezone.now()
        self.save()
    
    def get_status(self):
        """Get current stream status"""
        return {
            'is_active': self.is_active,
            'camera_status': self.camera.status,
            'camera_online': self.camera.is_online,
            'started_at': self.started_at,
            'duration': (timezone.now() - self.started_at).total_seconds() if self.started_at else 0,
            'quality_settings': self.quality_settings
        }


class CameraHealthLog(models.Model):
    """
    Log of camera health check results
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        related_name='health_logs',
        help_text="Camera that was checked"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Camera.STATUS_CHOICES,
        help_text="Camera status at time of check"
    )
    
    response_time = models.FloatField(
        help_text="Response time in seconds"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error message if health check failed"
    )
    
    checked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When health check was performed"
    )
    
    class Meta:
        ordering = ['-checked_at']
        verbose_name = 'Camera Health Log'
        verbose_name_plural = 'Camera Health Logs'
        indexes = [
            models.Index(fields=['camera', '-checked_at']),
            models.Index(fields=['status']),
            models.Index(fields=['-checked_at']),
        ]
    
    def __str__(self):
        return f"{self.camera.name} - {self.status} ({self.checked_at})"
    
    @property
    def is_healthy(self):
        """Check if this health check indicates camera is healthy"""
        return self.status == Camera.ONLINE
