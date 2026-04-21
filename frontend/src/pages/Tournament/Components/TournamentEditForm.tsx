import React from 'react';
import LoadingSpinner from '../../../components/LoadingSpinner/LoadingSpinner';
import { IconEdit, IconGlobe, IconCamera, IconAlert, IconSave } from '../../../components/Icons/Icons';

export interface TournamentEditFormProps {
    editForm: {
        name: string;
        description: string;
        max_participants: number;
        tournament_type: string;
        time_control: string;
        increment: number;
        is_public: boolean;
        vision_enabled: boolean;
        registration_deadline: string;
        start_date: string;
    };
    setEditForm: (form: any) => void;
    selectedTournament: any;
    actionLoading: string | null;
    onSave: () => void;
    onCancel: () => void;
}

const TournamentEditForm: React.FC<TournamentEditFormProps> = ({
    editForm,
    setEditForm,
    selectedTournament,
    actionLoading,
    onSave,
    onCancel
}) => {
    return (
        <div className="edit-form">
            <h3 className="edit-form-title flex-center-gap"><IconEdit size={24} /> Editar Torneio</h3>

            {/* Row 1: Name */}
            <div className="form-group">
                <label>Nome do Torneio</label>
                <input
                    type="text"
                    value={editForm.name}
                    onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                    className="game-input"
                />
            </div>

            {/* Row 2: Format + Max Participants */}
            <div className="form-row">
                <div className="form-group">
                    <label>Formato</label>
                    <select
                        value={editForm.tournament_type}
                        onChange={e => setEditForm({ ...editForm, tournament_type: e.target.value })}
                        className="game-select"
                        disabled={selectedTournament.status !== 'REGISTRATION'}
                    >
                        <option value="SWISS">Sistema Suíço</option>
                        <option value="ROUND_ROBIN">Todos Contra Todos</option>
                        <option value="ELIMINATION">Eliminação Direta</option>
                    </select>
                </div>
                <div className="form-group">
                    <label>Máx. Participantes</label>
                    <input
                        type="number"
                        min="2" max="256"
                        value={editForm.max_participants}
                        onChange={e => setEditForm({ ...editForm, max_participants: parseInt(e.target.value) })}
                        className="game-input"
                        disabled={selectedTournament.status !== 'REGISTRATION'}
                    />
                </div>
            </div>

            {/* Row 3: Time Control + Increment */}
            <div className="form-row">
                <div className="form-group">
                    <label>Controlo de Tempo</label>
                    <select
                        value={editForm.time_control}
                        onChange={e => setEditForm({ ...editForm, time_control: e.target.value })}
                        className="game-select"
                    >
                        <option value="">Selecionar...</option>
                        <option value="1+0">1 min (Bullet)</option>
                        <option value="2+1">2+1 min (Bullet)</option>
                        <option value="3+0">3 min (Blitz)</option>
                        <option value="3+2">3+2 min (Blitz)</option>
                        <option value="5+0">5 min (Blitz)</option>
                        <option value="5+3">5+3 min (Blitz)</option>
                        <option value="10+0">10 min (Rápido)</option>
                        <option value="10+5">10+5 min (Rápido)</option>
                        <option value="15+10">15+10 min (Rápido)</option>
                        <option value="30+0">30 min (Clássico)</option>
                        <option value="60+0">60 min (Clássico)</option>
                    </select>
                </div>
                <div className="form-group">
                    <label>Incremento (seg)</label>
                    <input
                        type="number"
                        min="0" max="60"
                        value={editForm.increment}
                        onChange={e => setEditForm({ ...editForm, increment: parseInt(e.target.value) || 0 })}
                        className="game-input"
                    />
                </div>
            </div>

            {/* Row 4: Registration Deadline + Start Date */}
            <div className="form-row">
                <div className="form-group">
                    <label>Prazo de Inscrição</label>
                    <input
                        type="datetime-local"
                        value={editForm.registration_deadline}
                        onChange={e => setEditForm({ ...editForm, registration_deadline: e.target.value })}
                        className="game-input"
                    />
                </div>
                <div className="form-group">
                    <label>Data de Início</label>
                    <input
                        type="datetime-local"
                        value={editForm.start_date}
                        onChange={e => setEditForm({ ...editForm, start_date: e.target.value })}
                        className="game-input"
                    />
                </div>
            </div>

            {/* Row 5: Toggles */}
            <div className="form-row">
                <div className="form-group toggle-group">
                    <label className="toggle-label">
                        <input
                            type="checkbox"
                            checked={editForm.is_public}
                            onChange={e => setEditForm({ ...editForm, is_public: e.target.checked })}
                            className="toggle-checkbox"
                        />
                        <span className="toggle-text flex-center-gap"><IconGlobe size={18} /> Torneio Público</span>
                    </label>
                    <span className="toggle-hint">Visível para todos os utilizadores</span>
                </div>
                <div className="form-group toggle-group">
                    <label className="toggle-label">
                        <input
                            type="checkbox"
                            checked={editForm.vision_enabled}
                            onChange={e => setEditForm({ ...editForm, vision_enabled: e.target.checked })}
                            className="toggle-checkbox"
                        />
                        <span className="toggle-text flex-center-gap"><IconCamera size={18} /> Vision AI Ativado</span>
                    </label>
                    <span className="toggle-hint">Reconhecimento automático de posições</span>
                </div>
            </div>

            {/* Row 6: Description */}
            <div className="form-group">
                <label>Descrição</label>
                <textarea
                    value={editForm.description}
                    onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                    className="game-input textarea"
                    rows={3}
                    placeholder="Descreve o torneio, regras especiais, prémios..."
                />
            </div>

            {selectedTournament.status !== 'REGISTRATION' && (
                <div className="edit-warning flex-center-gap">
                    <IconAlert size={20} /> Formato e capacidade não podem ser alterados após o torneio ter começado.
                </div>
            )}

            <div className="edit-actions">
                <button className="btn btn-secondary" onClick={onCancel}>Cancelar</button>
                <button className="btn btn-primary flex-center-gap" onClick={onSave} disabled={actionLoading === 'saving'}>
                    {actionLoading === 'saving' ? <LoadingSpinner size="small" /> : <><IconSave size={18} /> Guardar Alterações</>}
                </button>
            </div>
        </div>
    );
};

export default TournamentEditForm;