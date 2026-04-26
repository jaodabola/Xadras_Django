# XADRAS - Vistas de Torneio
# Implementação dos endpoints da API de Torneio

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
    ViewSet para gestão de Torneios
    Suporta operações CRUD e ações específicas de torneio
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar torneios com base nas permissões do utilizador"""
        user = self.request.user

        # Organizadores podem ver todos os seus torneios
        # Participantes podem ver torneios em que participam
        # Todos podem ver torneios públicos

        if self.action == 'list':
            # Para a vista de lista, mostrar torneios públicos e os do utilizador
            return Tournament.objects.filter(
                models.Q(is_public=True) |
                models.Q(created_by=user) |
                models.Q(participants__user=user)
            ).distinct().order_by('-created_at')
        else:
            # Para vistas de detalhe, permitir acesso aos torneios em que o utilizador está envolvido
            return Tournament.objects.filter(
                models.Q(created_by=user) |
                models.Q(participants__user=user) |
                models.Q(is_public=True)
            ).distinct()

    def get_serializer_class(self):
        """Retornar o serializer apropriado com base na ação"""
        if self.action == 'create':
            return TournamentCreateSerializer
        return TournamentSerializer

    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        """Criar um novo torneio"""
        if getattr(request.user, 'is_guest', False):
            return Response(
                {'error': 'Os convidados não podem criar torneios. Registe-se para criar um torneio.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tournament = serializer.save()

        # Adicionar automaticamente o criador como participante
        TournamentParticipant.objects.create(
            tournament=tournament,
            user=request.user,
            seed=1  # O criador do torneio recebe a semente 1
        )

        logger.info(
            f"Torneio criado: {tournament.name} por {request.user.username}")

        response_serializer = TournamentSerializer(
            tournament, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def join(self, request, pk=None):
        """Participar num torneio usando o código de adesão ou ID direto do torneio"""
        if getattr(request.user, 'is_guest', False):
            return Response(
                {'error': 'Os convidados não podem participar em torneios. Registe-se para jogar.'},
                status=status.HTTP_403_FORBIDDEN
            )

        tournament = self.get_object()

        # Verificar se o torneio aceita inscrições
        if tournament.status != Tournament.REGISTRATION:
            return Response(
                {'error': 'As inscrições no torneio estão fechadas'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if tournament.is_full:
            return Response(
                {'error': 'O torneio está cheio'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar se o utilizador já é um participante
        if TournamentParticipant.objects.filter(
            tournament=tournament,
            user=request.user
        ).exists():
            return Response(
                {'error': 'Já está registado neste torneio'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Adicionar utilizador como participante
        participant = TournamentParticipant.objects.create(
            tournament=tournament,
            user=request.user
        )

        logger.info(
            f"Utilizador {request.user.username} aderiu ao torneio {tournament.name}")

        serializer = TournamentParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Sair do torneio (apenas durante a inscrição)"""
        tournament = self.get_object()

        if tournament.status != Tournament.REGISTRATION:
            return Response(
                {'error': 'Não é possível sair do torneio após o fecho das inscrições'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            participant = TournamentParticipant.objects.get(
                tournament=tournament,
                user=request.user
            )

            # O criador do torneio não pode sair do seu próprio torneio
            if tournament.created_by == request.user:
                return Response(
                    {'error': 'O organizador do torneio não pode sair do seu próprio torneio'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            participant.delete()
            logger.info(
                f"Utilizador {request.user.username} saiu do torneio {tournament.name}")

            return Response(
                {'message': 'Saiu do torneio com sucesso'},
                status=status.HTTP_200_OK
            )

        except TournamentParticipant.DoesNotExist:
            return Response(
                {'error': 'Não está registado neste torneio'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Iniciar torneio (apenas organizador)"""
        tournament = self.get_object()

        # Verificar permissões
        if tournament.created_by != request.user:
            return Response(
                {'error': 'Apenas o organizador do torneio pode iniciar o torneio'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not tournament.can_start:
            return Response(
                {'error': 'O torneio não pode ser iniciado (verifique o número de participantes e o prazo de inscrição)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            manager = TournamentManager(tournament)
            result = manager.start_tournament(request.user)
            
            logger.info(
                f"Torneio iniciado: {tournament.name} com {tournament.participant_count} participantes")
                
            return Response(result)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                f"Erro ao iniciar o torneio {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Falha ao iniciar o torneio'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Obter participantes do torneio"""
        tournament = self.get_object()
        participants = tournament.participants.filter(
            is_active=True).order_by('seed')

        serializer = TournamentParticipantSerializer(participants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def standings(self, request, pk=None):
        """Obter a classificação atual do torneio com o sistema completo de desempates"""
        tournament = self.get_object()

        try:
            standings_data = calculate_tournament_standings(str(tournament.id))
            serializer = TournamentStandingsSerializer(
                standings_data, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(
                f"Erro ao calcular a classificação para o torneio {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Falha ao calcular a classificação'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def rounds(self, request, pk=None):
        """Obter as rondas do torneio"""
        tournament = self.get_object()
        rounds = tournament.rounds.all().order_by('round_number')

        serializer = TournamentRoundSerializer(rounds, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='rounds/(?P<round_number>[^/.]+)')
    def round_detail(self, request, pk=None, round_number=None):
        """Obter uma ronda específica com emparelhamentos"""
        tournament = self.get_object()

        try:
            round_obj = tournament.rounds.get(round_number=round_number)
        except TournamentRound.DoesNotExist:
            return Response(
                {'error': 'Ronda não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Obter dados da ronda
        round_serializer = TournamentRoundSerializer(round_obj)

        # Obter emparelhamentos para esta ronda
        pairings = round_obj.pairings.all().order_by('board_number')
        pairing_serializer = TournamentPairingSerializer(pairings, many=True)

        return Response({
            'round': round_serializer.data,
            'pairings': pairing_serializer.data
        })

    @action(detail=True, methods=['post'])
    def generate_pairings(self, request, pk=None):
        """Gerar emparelhamentos para a próxima ronda (apenas organizador)"""
        tournament = self.get_object()

        # Verificar permissões
        if tournament.created_by != request.user:
            return Response(
                {'error': 'Apenas o organizador do torneio pode gerar emparelhamentos'},
                status=status.HTTP_403_FORBIDDEN
            )

        if tournament.status != Tournament.IN_PROGRESS:
            return Response(
                {'error': 'O torneio não está em curso'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            manager = TournamentManager(tournament)
            result = manager.generate_next_round()

            # Converter emparelhamentos para usar o método to_dict() para uma resposta consistente da API
            if 'pairings' in result:
                # Obter os objetos TournamentPairing reais e serializá-los
                round_number = result['round_number']
                tournament_round = TournamentRound.objects.get(
                    tournament=tournament,
                    round_number=round_number
                )
                pairings = tournament_round.pairings.all()
                result['pairings'] = [pairing.to_dict()
                                      for pairing in pairings]

            logger.info(
                f"Gerados emparelhamentos para o torneio {tournament.name}, ronda {result['round_number']}")

            return Response(result, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                f"Erro ao gerar emparelhamentos para o torneio {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Falha ao gerar emparelhamentos'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def start_round(self, request, pk=None):
        """Iniciar uma ronda específica (apenas organizador)"""
        tournament = self.get_object()

        # Verificar permissões
        if tournament.created_by != request.user:
            return Response(
                {'error': 'Apenas o organizador do torneio pode iniciar rondas'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Usar round_number do body ou o current_round do torneio como fallback
        round_number = request.data.get('round_number') or tournament.current_round

        if not round_number:
            return Response(
                {'error': 'round_number é obrigatório e não há ronda ativa'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            manager = TournamentManager(tournament)
            result = manager.start_round(int(round_number))

            logger.info(
                f"Iniciada a ronda {round_number} para o torneio {tournament.name}")

            return Response(result)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                f"Erro ao iniciar a ronda para o torneio {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Falha ao iniciar a ronda'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def assign_boards(self, request, pk=None):
        """Atribuir tabuleiros físicos a emparelhamentos (apenas organizador)"""
        tournament = self.get_object()

        # Verificar permissões
        if tournament.created_by != request.user:
            return Response(
                {'error': 'Apenas o organizador do torneio pode atribuir tabuleiros'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Usar round_number do body ou o current_round do torneio como fallback
        round_number = request.data.get('round_number') or tournament.current_round

        if not round_number:
            return Response(
                {'error': 'round_number é obrigatório e não há ronda ativa'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Aceitar lista de assignments: [{pairing_id, physical_board_id, camera_id}]
        # ou dicionário legacy: {pairing_id: board_number}
        raw_assignments = request.data.get('assignments', request.data.get('board_assignments', {}))

        # Converter lista para dicionário indexado por pairing_id
        if isinstance(raw_assignments, list):
            board_assignments = {
                item['pairing_id']: {
                    'physical_board_id': item.get('physical_board_id'),
                    'camera_id': item.get('camera_id'),
                    'board_number': item.get('board_number'),
                }
                for item in raw_assignments
                if 'pairing_id' in item
            }
        else:
            board_assignments = raw_assignments

        try:
            manager = TournamentManager(tournament)
            result = manager.assign_boards_to_round(
                int(round_number), board_assignments)

            # Obter emparelhamentos atualizados com campos de IA de Visão
            tournament_round = TournamentRound.objects.get(
                tournament=tournament,
                round_number=round_number
            )
            updated_pairings = tournament_round.pairings.all()
            result['updated_pairings'] = [pairing.to_dict()
                                          for pairing in updated_pairings]

            logger.info(
                f"Tabuleiros atribuídos para o torneio {tournament.name}, ronda {round_number}")

            return Response(result)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                f"Erro ao atribuir tabuleiros para o torneio {tournament.id}: {str(e)}")
            return Response(
                {'error': 'Falha ao atribuir tabuleiros'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR

            )


class TournamentJoinByCodeView(viewsets.GenericViewSet):
    """
    Vista separada para aderir a torneios via código de adesão
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TournamentJoinSerializer

    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def create(self, request):
        """Participar num torneio usando o código de adesão"""
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
                {'error': 'Código de adesão inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar se o utilizador já é um participante
        if TournamentParticipant.objects.filter(
            tournament=tournament,
            user=request.user
        ).exists():
            return Response(
                {'error': 'Já está registado neste torneio'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Adicionar utilizador como participante
        participant = TournamentParticipant.objects.create(
            tournament=tournament,
            user=request.user
        )

        logger.info(
            f"Utilizador {request.user.username} aderiu ao torneio {tournament.name} via código de adesão")

        # Retornar detalhes do torneio
        tournament_serializer = TournamentSerializer(
            tournament, context={'request': request})
        return Response({
            'tournament': tournament_serializer.data,
            'participant': TournamentParticipantSerializer(participant).data
        }, status=status.HTTP_201_CREATED)
