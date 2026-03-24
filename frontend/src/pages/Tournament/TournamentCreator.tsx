import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTournament } from '../../contexts/TournamentContext';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner';
import './TournamentCreator.css';

interface TournamentFormData {
  name: string;
  description: string;
  max_participants: number;
  tournament_type: 'SWISS' | 'ROUND_ROBIN' | 'ELIMINATION';
  time_control: string;
  increment: number;
  vision_enabled: boolean;
  start_date?: string;
}

const TournamentCreator: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { createTournament, loading, error, clearError } = useTournament();

  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<TournamentFormData>({
    name: '',
    description: '',
    max_participants: 8,
    tournament_type: 'SWISS',
    time_control: '10+0',
    increment: 0,
    vision_enabled: false,
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const handleInputChange = (field: keyof TournamentFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear validation error when user starts typing
    if (validationErrors[field]) {
      setValidationErrors(prev => ({ ...prev, [field]: '' }));
    }
    clearError();
  };

  const validateStep = (step: number): boolean => {
    const errors: Record<string, string> = {};

    if (step === 1) {
      if (!formData.name.trim()) {
        errors.name = 'O nome do torneio é obrigatório';
      } else if (formData.name.length < 3) {
        errors.name = 'O nome deve ter pelo menos 3 caracteres';
      }

      if (!formData.description.trim()) {
        errors.description = 'A descrição do torneio é obrigatória';
      } else if (formData.description.length < 10) {
        errors.description = 'A descrição deve ter pelo menos 10 caracteres';
      }
    }

    if (step === 2) {
      if (formData.max_participants < 2) {
        errors.max_participants = 'São necessários pelo menos 2 participantes';
      } else if (formData.max_participants > 64) {
        errors.max_participants = 'Máximo de 64 participantes';
      }
    }

    if (step === 3) {
      if (!formData.time_control) {
        errors.time_control = 'O ritmo de jogo é obrigatório';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 4));
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const handleSubmit = async () => {
    if (!validateStep(currentStep)) return;

    try {
      const tournament = await createTournament(formData);
      navigate(`/tournaments/${tournament.id}`);
    } catch (err) {
      // Error is handled by context
    }
  };

  const renderStepIndicator = () => (
    <div className="step-indicator">
      {[1, 2, 3, 4].map(step => (
        <div
          key={step}
          className={`step ${currentStep >= step ? 'active' : ''} ${currentStep > step ? 'completed' : ''}`}
        >
          <div className="step-number">{step}</div>
          <div className="step-label">
            {step === 1 && 'Informação'}
            {step === 2 && 'Definições'}
            {step === 3 && 'Ritmo'}
            {step === 4 && 'Revisão'}
          </div>
        </div>
      ))}
    </div>
  );

  const renderStep1 = () => (
    <div className="form-step">
      <h2>Informação básica</h2>
      <p>Começe pelos detalhes essenciais do torneio.</p>

      <div className="form-group">
        <label htmlFor="name">Nome do Torneio *</label>
        <input
          id="name"
          type="text"
          value={formData.name}
          onChange={(e) => handleInputChange('name', e.target.value)}
          placeholder="Nome do torneio"
          className={validationErrors.name ? 'error' : ''}
        />
        {validationErrors.name && <span className="error-text">{validationErrors.name}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="description">Descrição *</label>
        <textarea
          id="description"
          value={formData.description}
          onChange={(e) => handleInputChange('description', e.target.value)}
          placeholder="Descreva o torneio…"
          rows={4}
          className={validationErrors.description ? 'error' : ''}
        />
        {validationErrors.description && <span className="error-text">{validationErrors.description}</span>}
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="form-step">
      <h2>Definições do torneio</h2>
      <p>Configure o formato e o limite de participantes.</p>

      <div className="form-group">
        <label htmlFor="max_participants">Máximo de Participantes *</label>
        <input
          id="max_participants"
          type="number"
          min="2"
          max="64"
          value={formData.max_participants}
          onChange={(e) => handleInputChange('max_participants', parseInt(e.target.value))}
          className={validationErrors.max_participants ? 'error' : ''}
        />
        {validationErrors.max_participants && <span className="error-text">{validationErrors.max_participants}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="tournament_type">Tipo de Torneio</label>
        <select
          id="tournament_type"
          value={formData.tournament_type}
          onChange={(e) => handleInputChange('tournament_type', e.target.value)}
        >
          <option value="SWISS">Sistema Suíço</option>
          <option value="ROUND_ROBIN">Round Robin</option>
          <option value="ELIMINATION">Eliminação Simples</option>
        </select>
        <small className="help-text">
          {formData.tournament_type === 'SWISS' && 'Os jogadores são emparelhados com base no desempenho e rating'}
          {formData.tournament_type === 'ROUND_ROBIN' && 'Todos os jogadores defrontam todos os outros'}
          {formData.tournament_type === 'ELIMINATION' && 'Torneio de eliminação direta'}
        </small>
      </div>

      <div className="form-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={formData.vision_enabled}
            onChange={(e) => handleInputChange('vision_enabled', e.target.checked)}
          />
          <span className="checkmark" />
          Ativar Integração de Visão IA
        </label>
        <small className="help-text">
          Permite rastrear tabuleiros físicos com câmara
        </small>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="form-step">
      <h2>Ritmo de Jogo</h2>
      <p>Define o tempo de jogo para as partidas do torneio.</p>

      <div className="form-group">
        <label>Predefinições de Ritmo</label>
        <div className="time-control-grid">
          {[
            { label: 'Bullet (1+0)', value: '1+0' },
            { label: 'Bullet (2+1)', value: '2+1' },
            { label: 'Blitz (3+0)', value: '3+0' },
            { label: 'Blitz (5+0)', value: '5+0' },
            { label: 'Rápido (10+0)', value: '10+0' },
            { label: 'Rápido (15+10)', value: '15+10' },
            { label: 'Clássico (30+0)', value: '30+0' },
            { label: 'Clássico (90+30)', value: '90+30' },
          ].map(preset => (
            <button
              key={preset.value}
              type="button"
              className={`time-preset ${formData.time_control === preset.value ? 'active' : ''}`}
              onClick={() => handleInputChange('time_control', preset.value)}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="custom_time">Ritmo Personalizado</label>
        <input
          id="custom_time"
          type="text"
          value={formData.time_control}
          onChange={(e) => handleInputChange('time_control', e.target.value)}
          placeholder="ex. 10+5"
          className={validationErrors.time_control ? 'error' : ''}
        />
        <small className="help-text">
          Formato: minutos+incremento (ex. 10+5 = 10 min + 5 seg por jogada)
        </small>
        {validationErrors.time_control && <span className="error-text">{validationErrors.time_control}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="start_date">Data de Início (Opcional)</label>
        <input
          id="start_date"
          type="datetime-local"
          min={new Date(new Date().getTime() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16)}
          value={formData.start_date || ''}
          onChange={(e) => {
            const val = e.target.value;
            if (!val) {
              handleInputChange('start_date', '');
              return;
            }
            
            // Check if user typed a date in the past
            const selectedDate = new Date(val);
            const now = new Date();
            // Allow 60 seconds of grace period for slow typers/current time bounds
            if (selectedDate.getTime() < now.getTime() - 60000) {
               // Revert/Force to current local time min string
               const currentMin = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
               handleInputChange('start_date', currentMin);
            } else {
               handleInputChange('start_date', val);
            }
          }}
        />
        <small className="help-text">
          Deixe em branco para iniciar o torneio de imediato
        </small>
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="form-step">
      <h2>Rever Torneio</h2>
      <p>Confirme as definições antes de criar o torneio.</p>

      <div className="review-section">
        <div className="review-item">
          <label>Nome</label>
          <span>{formData.name}</span>
        </div>
        <div className="review-item">
          <label>Descrição</label>
          <span>{formData.description}</span>
        </div>
        <div className="review-item">
          <label>Máx. Participantes</label>
          <span>{formData.max_participants}</span>
        </div>
        <div className="review-item">
          <label>Tipo</label>
          <span>{formData.tournament_type.replace('_', ' ')}</span>
        </div>
        <div className="review-item">
          <label>Ritmo de Jogo</label>
          <span>{formData.time_control}</span>
        </div>
        <div className="review-item">
          <label>Visão IA</label>
          <span>{formData.vision_enabled ? 'Ativo' : 'Inativo'}</span>
        </div>
        {formData.start_date && (
          <div className="review-item">
            <label>Data de Início</label>
            <span>{new Date(formData.start_date).toLocaleString('pt-PT')}</span>
          </div>
        )}
      </div>
    </div>
  );

  if (!user) {
    return (
      <div className="tournament-creator">
        <div className="auth-required">
          <h2>Autenticação necessária</h2>
          <p>Inicie sessão para criar torneios.</p>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/login')}
          >
            Iniciar Sessão
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="tournament-creator">
      <div className="creator-container">
        <div className="creator-header">
          <button
            className="back-button"
            onClick={() => navigate('/tournaments')}
          >
            ← Torneios
          </button>
          <h1>Criar Torneio</h1>
        </div>

        {renderStepIndicator()}

        {error && (
          <div className="error-banner">
            <span className="error-message">{error}</span>
            <button className="error-close" onClick={clearError}>×</button>
          </div>
        )}

        <div className="creator-content">
          {currentStep === 1 && renderStep1()}
          {currentStep === 2 && renderStep2()}
          {currentStep === 3 && renderStep3()}
          {currentStep === 4 && renderStep4()}
        </div>

        <div className="creator-actions">
          {currentStep > 1 && (
            <button
              className="btn btn-secondary"
              onClick={prevStep}
              disabled={loading}
            >
              Anterior
            </button>
          )}

          {currentStep < 4 ? (
            <button
              className="btn btn-primary"
              onClick={nextStep}
            >
              Seguinte
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? <LoadingSpinner /> : 'Criar Torneio'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TournamentCreator;
