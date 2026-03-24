# XADRAS - Camera & Stream Serializers
# Implementation for Camera/Stream API endpoints

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Camera, Stream, CameraHealthLog

User = get_user_model()

class CameraSerializer(serializers.ModelSerializer):
    """Serializer for Camera model"""
    
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    is_online = serializers.ReadOnlyField()
    current_stream = serializers.SerializerMethodField()
    
    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'description', 'camera_type', 'connection_url',
            'ip_address', 'port', 'username', 'password', 'location',
            'is_active', 'status', 'last_health_check', 'calibration_data',
            'is_calibrated', 'created_by', 'created_by_username', 'is_online',
            'current_stream', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'last_health_check', 'created_by', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},  # Don't expose password in responses
        }
    
    def get_current_stream(self, obj):
        """Get current active stream for this camera"""
        stream = obj.current_stream
        if stream:
            return {
                'id': stream.id,
                'game_id': stream.game.id,
                'is_active': stream.is_active,
                'started_at': stream.started_at
            }
        return None
    
    def create(self, validated_data):
        """Create camera with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CameraCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for camera creation"""
    
    class Meta:
        model = Camera
        fields = [
            'name', 'description', 'camera_type', 'connection_url',
            'username', 'password', 'location'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def create(self, validated_data):
        """Create camera with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class StreamSerializer(serializers.ModelSerializer):
    """Serializer for Stream model"""
    
    camera_name = serializers.CharField(source='camera.name', read_only=True)
    camera_location = serializers.CharField(source='camera.location', read_only=True)
    game_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Stream
        fields = [
            'id', 'camera', 'camera_name', 'camera_location', 'game', 'game_info',
            'is_active', 'started_at', 'ended_at', 'quality_settings',
            'recording_enabled', 'recording_path', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_game_info(self, obj):
        """Get basic game information"""
        game = obj.game
        return {
            'id': game.id,
            'white_player': game.white_player.username,
            'black_player': game.black_player.username if game.black_player else None,
            'status': game.status
        }


class StreamAttachSerializer(serializers.Serializer):
    """Serializer for attaching camera to game"""
    
    camera_id = serializers.UUIDField()
    game_id = serializers.UUIDField()
    quality_settings = serializers.JSONField(required=False)
    recording_enabled = serializers.BooleanField(default=False)
    
    def validate_camera_id(self, value):
        """Validate camera exists and is available"""
        try:
            camera = Camera.objects.get(id=value)
        except Camera.DoesNotExist:
            raise serializers.ValidationError("Camera not found")
        
        if not camera.is_active:
            raise serializers.ValidationError("Camera is not active")
        
        if not camera.is_online:
            raise serializers.ValidationError("Camera is not online")
        
        # Check if camera already has an active stream
        if camera.current_stream:
            raise serializers.ValidationError("Camera is already streaming")
        
        return value
    
    def validate_game_id(self, value):
        """Validate game exists and is in progress"""
        from game.models import Game
        
        try:
            game = Game.objects.get(id=value)
        except Game.DoesNotExist:
            raise serializers.ValidationError("Game not found")
        
        if game.status != 'IN_PROGRESS':
            raise serializers.ValidationError("Game is not in progress")
        
        return value


class CameraHealthLogSerializer(serializers.ModelSerializer):
    """Serializer for Camera Health Log"""
    
    camera_name = serializers.CharField(source='camera.name', read_only=True)
    is_healthy = serializers.ReadOnlyField()
    
    class Meta:
        model = CameraHealthLog
        fields = [
            'id', 'camera', 'camera_name', 'status', 'response_time',
            'error_message', 'is_healthy', 'checked_at'
        ]
        read_only_fields = ['id', 'checked_at']


class CameraTestSerializer(serializers.Serializer):
    """Serializer for camera connection test"""
    
    def validate(self, data):
        """Test camera connection"""
        camera = self.instance
        if not camera:
            raise serializers.ValidationError("Camera instance required")
        
        return data


class CameraCalibrationSerializer(serializers.Serializer):
    """Serializer for camera calibration data"""
    
    calibration_data = serializers.JSONField()
    
    def validate_calibration_data(self, value):
        """Validate calibration data structure"""
        required_fields = ['corners', 'board_size', 'square_size']
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Calibration data must be a dictionary")
        
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")
        
        return value


class CameraStatusSerializer(serializers.Serializer):
    """Serializer for camera status information"""
    
    id = serializers.UUIDField()
    name = serializers.CharField()
    location = serializers.CharField()
    status = serializers.CharField()
    is_online = serializers.BooleanField()
    last_health_check = serializers.DateTimeField()
    is_calibrated = serializers.BooleanField()
    current_stream = serializers.DictField(allow_null=True)
    response_time = serializers.FloatField(allow_null=True)
    error_message = serializers.CharField(allow_blank=True)
