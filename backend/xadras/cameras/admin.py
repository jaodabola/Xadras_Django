# XADRAS - Camera & Stream Admin
# Django admin configuration for camera and stream models

from django.contrib import admin
from django.utils.html import format_html
from .models import Camera, Stream, CameraHealthLog

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'location', 'camera_type', 'status_indicator', 
        'is_active', 'is_calibrated', 'created_by', 'last_health_check'
    ]
    list_filter = ['camera_type', 'status', 'is_active', 'is_calibrated', 'created_at']
    search_fields = ['name', 'location', 'ip_address', 'created_by__username']
    readonly_fields = ['id', 'status', 'last_health_check', 'is_online', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location')
        }),
        ('Camera Configuration', {
            'fields': ('camera_type', 'connection_url', 'ip_address', 'port')
        }),
        ('Authentication', {
            'fields': ('username', 'password'),
            'classes': ('collapse',)
        }),
        ('Status & Health', {
            'fields': ('is_active', 'status', 'last_health_check', 'is_online')
        }),
        ('Vision AI Integration', {
            'fields': ('is_calibrated', 'calibration_data'),
            'classes': ('collapse',)
        }),
        ('Management', {
            'fields': ('created_by',)
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_indicator(self, obj):
        """Display colored status indicator"""
        colors = {
            'ONLINE': 'green',
            'OFFLINE': 'gray',
            'ERROR': 'red',
            'CALIBRATING': 'orange',
            'MAINTENANCE': 'blue'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_indicator.short_description = 'Status'
    
    actions = ['test_cameras', 'activate_cameras', 'deactivate_cameras']
    
    def test_cameras(self, request, queryset):
        """Test selected cameras"""
        tested_count = 0
        for camera in queryset:
            try:
                camera.health_check()
                tested_count += 1
            except Exception:
                pass
        
        self.message_user(request, f'Tested {tested_count} cameras')
    test_cameras.short_description = 'Test selected cameras'
    
    def activate_cameras(self, request, queryset):
        """Activate selected cameras"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} cameras')
    activate_cameras.short_description = 'Activate selected cameras'
    
    def deactivate_cameras(self, request, queryset):
        """Deactivate selected cameras"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} cameras')
    deactivate_cameras.short_description = 'Deactivate selected cameras'

@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = [
        'camera', 'game_info', 'is_active', 'started_at', 
        'ended_at', 'recording_enabled', 'created_at'
    ]
    list_filter = ['is_active', 'recording_enabled', 'created_at']
    search_fields = ['camera__name', 'game__id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Stream Configuration', {
            'fields': ('camera', 'game', 'is_active')
        }),
        ('Timing', {
            'fields': ('started_at', 'ended_at')
        }),
        ('Quality & Recording', {
            'fields': ('quality_settings', 'recording_enabled', 'recording_path')
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def game_info(self, obj):
        """Display game information"""
        game = obj.game
        return f"Game {game.id}: {game.white_player.username} vs {game.black_player.username if game.black_player else 'Waiting'}"
    game_info.short_description = 'Game'
    
    actions = ['stop_streams']
    
    def stop_streams(self, request, queryset):
        """Stop selected active streams"""
        stopped_count = 0
        for stream in queryset.filter(is_active=True):
            stream.stop_stream()
            stopped_count += 1
        
        self.message_user(request, f'Stopped {stopped_count} streams')
    stop_streams.short_description = 'Stop selected streams'

@admin.register(CameraHealthLog)
class CameraHealthLogAdmin(admin.ModelAdmin):
    list_display = [
        'camera', 'status_indicator', 'response_time', 
        'is_healthy', 'checked_at'
    ]
    list_filter = ['status', 'camera', 'checked_at']
    search_fields = ['camera__name', 'error_message']
    readonly_fields = ['id', 'is_healthy', 'checked_at']
    
    fieldsets = (
        ('Health Check', {
            'fields': ('camera', 'status', 'response_time', 'is_healthy')
        }),
        ('Error Information', {
            'fields': ('error_message',)
        }),
        ('System', {
            'fields': ('id', 'checked_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_indicator(self, obj):
        """Display colored status indicator"""
        colors = {
            'ONLINE': 'green',
            'OFFLINE': 'gray',
            'ERROR': 'red',
            'CALIBRATING': 'orange',
            'MAINTENANCE': 'blue'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_indicator.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Disable manual creation of health logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of health logs"""
        return False
