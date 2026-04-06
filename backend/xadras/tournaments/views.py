# XADRAS - Tournament Views
# Implementation of Tournament API endpoints

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import logging

from .models import Tournament, TournamentParticipant, TournamentRound, TournamentPairing
from .serializers import (
    TournamentSerializer, TournamentCreateSerializer, TournamentJoinSerializer,
    TournamentParticipantSerializer, TournamentRoundSerializer, 
    TournamentPairingSerializer, TournamentStandingsSerializer
)
from .tournament_manager import TournamentManager, generate_tournament_round
from .standings_calculator import calculate_tournament_standings

User = get_user_model()
logger = logging.getLogger(__name__)

class TournamentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Tournament management
    Supports CRUD operations and tournament-specific actions
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter tournaments based on user permissions"""
        user = self.request.user
        
        # Organizers can see all their tournaments
        # Participants can see tournaments they're in
        # Everyone can see public tournaments
        
        if self.action == 'list':
            # For list view, show public tournaments and user's tournaments
            return Tournament.objects.filter(
                models.Q(is_public=True) |
                models.Q(created_by=user) |
                models.Q(participants__user=user)
            ).distinct().order_by('-created_at')
        else:
            # For detail views, allow access to tournaments user is involved in
            return Tournament.objects.filter(
                models.Q(created_by=user) |
                models.Q(participants__user=user) |
                models.Q(is_public=True)
            ).distinct()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return TournamentCreateSerializer
        return TournamentSerializer
    
    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        """Create a new tournament"""
        if getattr(request.user, 'is_guest', False):
            return Response(
                {'error': 'Os convidados não podem criar torneios. Registe-se para criar um torneio.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tournament = serializer.save()
        
        # Automatically add creator as participant
        TournamentParticipant.objects.create(
            tournament=tournament,
            user=request.user,
            seed=1  # Tournament creator gets seed 1
        )
        
        logger.info(f"Tournament created: {tournament.name} by {request.user.username}")
        
        response_serializer = TournamentSerializer(tournament, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def join(self, request, pk=None):
        """Join tournament using join code or direct tournament ID"""
        if getattr(request.user, 'is_guest', False):
            return Response(
                {'error': 'Os convidados não podem participar em torneios. Registe-se para jogar.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tournament = self.get_object()
        
        # Check if tournament is joinable
        if tournament.status != Tournament.REGISTRATION:
            return Response(
                {'error': 'Tournament registration is closed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if tournament.is_full:
            return Response(
                {'error': 'Tournament is full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is already a participant
        if TournamentParticipant.objects.filter(
            tournament=tournament, 
            user=request.user
        ).exists():
            return Response(
                {'error': 'You are already registered for this tournament'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add user as participant
        participant = TournamentParticipant.objects.create(
            tournament=tournament,
            user=request.user
        )
        
        logger.info(f"User {request.user.username} joined tournament {tournament.name}")
        
        serializer = TournamentParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave tournament (only during registration)"""
        tournament = self.get_object()
        
        if tournament.status != Tournament.REGISTRATION:
            return Response(
                {'error': 'Cannot leave tournament after registration closes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = TournamentParticipant.objects.get(
                tournament=tournament,
                user=request.user
            )
            
            # Tournament creator cannot leave their own tournament
            if tournament.created_by == request.user:
                return Response(
                    {'error': 'Tournament organizer cannot leave their own tournament'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            participant.delete()
            logger.info(f"User {request.user.username} left tournament {tournament.name}")
            
            return Response(
                {'message': 'Successfully left tournament'},
                status=status.HTTP_200_OK
            )
            
        except TournamentParticipant.DoesNotExist:
            return Response(
                {'error': 'You are not registered for this tournament'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start tournament (organizer only)"""
        tournament = self.get_object()
        
        # Check permissions
        if tournament.created_by != request.user:
            return Response(
                {'error': 'Only tournament organizer can start tournament'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not tournament.can_start:
            return Response(
                {'error': 'Tournament cannot be started (check participant count and registration deadline)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Update tournament status
            tournament.status = Tournament.IN_PROGRESS
            tournament.start_date = timezone.now()
            
            # Calculate total rounds for Swiss system
            if tournament.tournament_type == Tournament.SWISS:
                participant_count = tournament.participant_count
                if participant_count >= 2:
                    import math
                    tournament.total_rounds = math.ceil(math.log2(participant_count))
            
            tournament.save()
            
            # Assign seeds based on rating
            participants = tournament.participants.filter(is_active=True).order_by('-initial_rating')
            for i, participant in enumerate(participants, 1):
                participant.seed = i
                participant.save()
            
            logger.info(f"Tournament started: {tournament.name} with {tournament.participant_count} participants")
        
        serializer = TournamentSerializer(tournament, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get tournament participants"""
        tournament = self.get_object()
        participants = tournament.participants.filter(is_active=True).order_by('seed')
        
        serializer = TournamentParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def standings(self, request, pk=None):
        """Get current tournament standings with complete tiebreaker system"""
        tournament = self.get_object()
        
        try:
            standings_data = calculate_tournament_standings(str(tournament.id))
            serializer = TournamentStandingsSerializer(standings_data, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error calculating standings for tournament {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Failed to calculate standings'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def rounds(self, request, pk=None):
        """Get tournament rounds"""
        tournament = self.get_object()
        rounds = tournament.rounds.all().order_by('round_number')
        
        serializer = TournamentRoundSerializer(rounds, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='rounds/(?P<round_number>[^/.]+)')
    def round_detail(self, request, pk=None, round_number=None):
        """Get specific round with pairings"""
        tournament = self.get_object()
        
        try:
            round_obj = tournament.rounds.get(round_number=round_number)
        except TournamentRound.DoesNotExist:
            return Response(
                {'error': 'Round not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get round data
        round_serializer = TournamentRoundSerializer(round_obj)
        
        # Get pairings for this round
        pairings = round_obj.pairings.all().order_by('board_number')
        pairing_serializer = TournamentPairingSerializer(pairings, many=True)
        
        return Response({
            'round': round_serializer.data,
            'pairings': pairing_serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def generate_pairings(self, request, pk=None):
        """Generate pairings for next round (organizer only)"""
        tournament = self.get_object()
        
        # Check permissions
        if tournament.created_by != request.user:
            return Response(
                {'error': 'Only tournament organizer can generate pairings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if tournament.status != Tournament.IN_PROGRESS:
            return Response(
                {'error': 'Tournament is not in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            manager = TournamentManager(tournament)
            result = manager.generate_next_round()
            
            # Convert pairings to use to_dict() method for consistent API response
            if 'pairings' in result:
                # Get actual TournamentPairing objects and serialize them
                round_number = result['round_number']
                tournament_round = TournamentRound.objects.get(
                    tournament=tournament,
                    round_number=round_number
                )
                pairings = tournament_round.pairings.all()
                result['pairings'] = [pairing.to_dict() for pairing in pairings]
            
            logger.info(f"Generated pairings for tournament {tournament.name}, round {result['round_number']}")
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error generating pairings for tournament {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Failed to generate pairings'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def start_round(self, request, pk=None):
        """Start a specific round (organizer only)"""
        tournament = self.get_object()
        
        # Check permissions
        if tournament.created_by != request.user:
            return Response(
                {'error': 'Only tournament organizer can start rounds'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        round_number = request.data.get('round_number')
        if not round_number:
            return Response(
                {'error': 'round_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            manager = TournamentManager(tournament)
            result = manager.start_round(int(round_number))
            
            logger.info(f"Started round {round_number} for tournament {tournament.name}")
            
            return Response(result)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error starting round for tournament {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Failed to start round'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def assign_boards(self, request, pk=None):
        """Assign physical boards to pairings (organizer only)"""
        tournament = self.get_object()
        
        # Check permissions
        if tournament.created_by != request.user:
            return Response(
                {'error': 'Only tournament organizer can assign boards'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        round_number = request.data.get('round_number')
        board_assignments = request.data.get('board_assignments', {})
        
        if not round_number:
            return Response(
                {'error': 'round_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            manager = TournamentManager(tournament)
            result = manager.assign_boards_to_round(int(round_number), board_assignments)
            
            # Get updated pairings with Vision AI fields
            tournament_round = TournamentRound.objects.get(
                tournament=tournament,
                round_number=round_number
            )
            updated_pairings = tournament_round.pairings.all()
            result['updated_pairings'] = [pairing.to_dict() for pairing in updated_pairings]
            
            logger.info(f"Assigned boards for tournament {tournament.name}, round {round_number}")
            
            return Response(result)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error assigning boards for tournament {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Failed to assign boards'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TournamentJoinByCodeView(viewsets.GenericViewSet):
    """
    Separate view for joining tournaments by join code
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TournamentJoinSerializer
    
    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def create(self, request):
        """Join tournament using join code"""
        if getattr(request.user, 'is_guest', False):
            return Response(
                {'error': 'Os convidados não podem participar em torneios. Registe-se para jogar.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        join_code = serializer.validated_data['join_code'].upper()
        
        try:
            tournament = Tournament.objects.get(join_code=join_code)
        except Tournament.DoesNotExist:
            return Response(
                {'error': 'Invalid join code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is already a participant
        if TournamentParticipant.objects.filter(
            tournament=tournament, 
            user=request.user
        ).exists():
            return Response(
                {'error': 'You are already registered for this tournament'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add user as participant
        participant = TournamentParticipant.objects.create(
            tournament=tournament,
            user=request.user
        )
        
        logger.info(f"User {request.user.username} joined tournament {tournament.name} via join code")
        
        # Return tournament details
        tournament_serializer = TournamentSerializer(tournament, context={'request': request})
        return Response({
            'tournament': tournament_serializer.data,
            'participant': TournamentParticipantSerializer(participant).data
        }, status=status.HTTP_201_CREATED)
