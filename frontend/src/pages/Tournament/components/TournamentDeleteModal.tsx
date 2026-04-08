import React from 'react';
import LoadingSpinner from '../../../components/LoadingSpinner/LoadingSpinner';

export interface TournamentDeleteModalProps {
  isOpen: boolean;
  tournamentName?: string;
  actionLoading: string | null;
  onClose: () => void;
  onConfirm: () => void;
}

const TournamentDeleteModal: React.FC<TournamentDeleteModalProps> = ({
  isOpen,
  tournamentName,
  actionLoading,
  onClose,
  onConfirm
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-icon">🗑️</div>
        <h3>Apagar Torneio</h3>
        <p>
          Tem a certeza que pretende apagar o torneio{' '}
          <strong>{tournamentName}</strong>?
        </p>
        <div className="modal-warning-text">
          ⚠️ Esta ação é irreversível. Todos os dados, participantes e histórico de jogos associados serão permanentemente eliminados.
        </div>
        <div className="modal-actions">
          <button
            className="btn-delete-cancel"
            onClick={onClose}
            disabled={actionLoading === 'deleting'}
          >
            Cancelar
          </button>
          <button
            className="btn-delete-confirm"
            onClick={onConfirm}
            disabled={actionLoading === 'deleting'}
          >
            {actionLoading === 'deleting' ? <LoadingSpinner size="small" /> : '🗑 Apagar Definitivamente'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TournamentDeleteModal;
