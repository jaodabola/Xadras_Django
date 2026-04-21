import React, { useState, useEffect, useRef } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { IconStar } from '../../components/Icons/Icons';
import './Profile.css';

const Profile: React.FC = () => {
    const { user, updateProfile } = useAuth();

    const [formData, setFormData] = useState({
        username: '',
        email: ''
    });

    const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        if (user) {
            setFormData({
                username: user.username || '',
                email: user.email || ''
            });
            if (user.avatar) {
                setAvatarPreview(user.avatar);
            }
        }
    }, [user]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            setSelectedFile(file);

            const reader = new FileReader();
            reader.onloadend = () => {
                setAvatarPreview(reader.result as string);
            };
            reader.readAsDataURL(file);
        }
    };

    const triggerFileInput = () => {
        if (!user?.isGuest) {
            fileInputRef.current?.click();
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setLoading(true);

        try {
            if (selectedFile) {
                // Enviar com FormData se houver uma nova imagem
                const data = new FormData();
                data.append('username', formData.username);
                if (formData.email) data.append('email', formData.email);
                data.append('avatar', selectedFile);

                await updateProfile(data);
            } else {
                // Enviar como JSON normal se for só texto
                await updateProfile(formData);
            }

            setSuccess('Perfil atualizado com sucesso!');
            setSelectedFile(null); // Limpar seleção de ficheiro
        } catch (err: any) {
            setError(err.message || 'Falha ao atualizar o perfil. Verifica os dados introduzidos.');
        } finally {
            setLoading(false);
        }
    };

    if (!user) return null;
    if (user.isGuest) return <Navigate to="/" replace />;

    return (
        <div className="profile-container">
            <div className="profile-wrapper">

                <div className="profile-banner">
                    <div className="avatar-wrapper" onClick={triggerFileInput}>
                        <div className={`avatar-container ${!user.isGuest ? 'editable' : ''}`}>
                            {avatarPreview ? (
                                <img src={avatarPreview} alt="Avatar" className="avatar-image" />
                            ) : (
                                <div className="avatar-placeholder">
                                    {user.username.charAt(0).toUpperCase()}
                                </div>
                            )}
                            {!user.isGuest && (
                                <div className="avatar-overlay">
                                    <span>Alterar</span>
                                </div>
                            )}
                        </div>

                        {/* Input escondido para a imagem */}
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            accept="image/jpeg,image/png,image/gif"
                            style={{ display: 'none' }}
                        />
                    </div>

                    <div className="profile-name-info">
                        <h1 className="profile-username">
                            {user.username}
                            {user.isGuest && <span className="guest-badge">Guest</span>}
                        </h1>
                        <div className="profile-elo-badge">
                            <span className="elo-icon"><IconStar size={16} /></span> ELO {user.elo_rating || 1200}
                        </div>
                    </div>
                </div>

                {/* Mensagens de Feedback */}
                {(error || success) && (
                    <div className="feedback-section">
                        {error && <div className="error-message">{error}</div>}
                        {success && <div className="success-message">{success}</div>}
                    </div>
                )}

                <div className="profile-content">

                    {/* Card Estatísticas (Esquerda) */}
                    <div className="profile-card stats-section">
                        <h2 className="card-title">Estatísticas</h2>

                        <div className="stats-list">
                            <div className="stat-row">
                                <span className="stat-label">Total Partidas</span>
                                <span className="stat-val">{user.games_played || 0}</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">Vitórias</span>
                                <span className="stat-val win">{user.games_won || 0}</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">Derrotas</span>
                                <span className="stat-val loss">{user.games_lost || 0}</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">Empates</span>
                                <span className="stat-val draw">{user.games_drawn || 0}</span>
                            </div>
                        </div>

                        {/* Win Rate Bar Chart */}
                        <div className="win-rate-container">
                            <div className="win-rate-header">
                                <span>Taxa de Vitória</span>
                                <span>{user.games_played ? Math.round((user.games_won || 0) / user.games_played * 100) : 0}%</span>
                            </div>
                            <div className="win-rate-bar">
                                <div className="bar-win" title="Vitórias" style={{ width: `${user.games_played ? ((user.games_won || 0) / user.games_played * 100) : 0}%` }}></div>
                                <div className="bar-draw" title="Empates" style={{ width: `${user.games_played ? ((user.games_drawn || 0) / user.games_played * 100) : 0}%` }}></div>
                            </div>
                        </div>
                    </div>

                    {/* Card Definições da Conta (Direita) */}
                    <div className="profile-card settings-section">
                        <h2 className="card-title">Opções da Conta</h2>

                        <form className="profile-form" onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label htmlFor="username">Username</label>
                                <input
                                    type="text"
                                    id="username"
                                    name="username"
                                    value={formData.username}
                                    onChange={handleChange}
                                    disabled={user.isGuest}
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label htmlFor="email">Email</label>
                                <input
                                    type="email"
                                    id="email"
                                    name="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    disabled={user.isGuest}
                                />
                            </div>

                            <button
                                type="submit"
                                className="btn btn-primary btn-save"
                                disabled={loading || user.isGuest || (!selectedFile && user.username === formData.username && user.email === formData.email)}
                            >
                                {loading ? 'A guardar...' : 'Guardar Alterações'}
                            </button>

                            {user.isGuest && (
                                <p className="guest-warning">
                                    Contas de convidado não podem alterar as suas informações ou avatar.
                                </p>
                            )}
                        </form>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default Profile;