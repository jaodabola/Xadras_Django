import axios from 'axios';

const API_URL = 'http://192.168.1.8:8000/api';

// Criar instância do axios com URL base
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Adicionar token aos pedidos se disponível
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
      method: config.method,
      url: config.url,
      data: config.data,
      headers: config.headers
    });
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Lidar com respostas 401 Não Autorizado
api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      status: response.status,
      data: response.data,
      headers: response.headers
    });
    return response;
  },
  (error) => {
    console.error('[API Error]', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });

    if (error.response?.status === 401) {
      // Limpar dados de autenticação se recebermos 401
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      localStorage.removeItem('isGuest');
      // Redirecionar para a página de login se não estiver lá
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const auth = {
  // Delete guest user
  deleteGuest: async () => {
    console.log('[DEBUG] deleteGuest called');
    try {
      const response = await api.delete('/accounts/guest/delete/');
      console.log('[DEBUG] deleteGuest success', response);
    } catch (error) {
      console.error('[DEBUG] Failed to delete guest user:', error);
    }
  },
  // Login como convidado
  guestLogin: async () => {
    try {
      const response = await api.post('/accounts/guest/');
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('username', response.data.username);
      localStorage.setItem('isGuest', 'true');
      return response.data;
    } catch (error) {
      console.error('Guest login failed:', error);
      throw error;
    }
  },

  // Login regular
  login: async (username: string, password: string) => {
    try {
      const response = await api.post('/token/login/', {
        username,
        password
      });

      if (response.data.auth_token) {
        localStorage.setItem('token', response.data.auth_token);
        localStorage.setItem('username', username);
        localStorage.setItem('isGuest', 'false');

        // Obter dados do utilizador
        const userResponse = await api.get('/users/me/');
        return { ...response.data, user: userResponse.data };
      }
      throw new Error('Nenhum token de autenticação recebido');
    } catch (error: any) {
      console.error('Login failed:', error.response?.data || error.message);
      throw error.response?.data || { message: 'Falha no login. Por favor, verifique as suas credenciais.' };
    }
  },

  // Registar novo utilizador
  register: async (username: string, email: string, password: string) => {
    try {
      // Primeiro, criar o utilizador
      const response = await api.post('/users/', {
        username,
        email,
        password,
        re_password: password
      });

      if (response.status === 201) {
        // Após o registo bem-sucedido, fazer login
        try {
          return await auth.login(username, password);
        } catch (loginError) {
          // Se o login após o registo falhar, ainda assim considerar o registo bem-sucedido
          // mas informar o utilizador que precisa de fazer login manualmente
          return {
            success: true,
            message: 'Registo bem-sucedido! Por favor, faça login com as suas credenciais.',
            requiresLogin: true
          };
        }
      }

      return response.data;
    } catch (error: any) {
      console.error('Registration failed:', error.response?.data || error.message);

      // Lidar com casos de erro específicos
      let errorMessage = 'Falha no registo';
      const errorData = error.response?.data || {};

      if (errorData.username) {
        errorMessage = `Username: ${Array.isArray(errorData.username) ? errorData.username.join(' ') : errorData.username}`;
      } else if (errorData.email) {
        errorMessage = `Email: ${Array.isArray(errorData.email) ? errorData.email.join(' ') : errorData.email}`;
      } else if (errorData.password) {
        errorMessage = `Password: ${Array.isArray(errorData.password) ? errorData.password.join(' ') : errorData.password}`;
      } else if (errorData.non_field_errors) {
        errorMessage = Array.isArray(errorData.non_field_errors)
          ? errorData.non_field_errors.join(' ')
          : errorData.non_field_errors;
      }

      throw { message: errorMessage, details: errorData };
    }
  },

  // Terminar sessão
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('isGuest');
  },

  // Obter utilizador atual
  getCurrentUser: async () => {
    try {
      const response = await api.get('/users/me/');
      return response.data;
    } catch (error: any) {
      console.error('Failed to get user profile:', error.response?.data || error.message);
      // If we can't get the user profile, clear the invalid token
      if (error.response?.status === 401) {
        auth.logout();
      }
      throw error.response?.data || { message: 'Falha ao obter o perfil do utilizador' };
    }
  },

  // Atualizar perfil do utilizador (incluindo Avatar)
  updateProfile: async (data: { username?: string; email?: string } | FormData) => {
    try {
      const isFormData = data instanceof FormData;
      const config = isFormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined;

      // Use PATCH instead of PUT for partial updates
      const response = await api.patch('/users/me/', data, config);

      // Se o username foi alterado com sucesso, atualizar localStorage
      const updatedUsername = isFormData ? data.get('username') : data.username;

      if (updatedUsername && response.data.username) {
        localStorage.setItem('username', response.data.username);
      }

      return response.data;
    } catch (error: any) {
      console.error('Failed to update user profile:', error.response?.data || error.message);
      const errorData = error.response?.data || {};
      throw { message: 'Falha ao atualizar o perfil. Verifica os dados e tenta novamente.', details: errorData };
    }
  },
};

export const matchmaking = {
  // Entrar na fila de jogo
  joinQueue: async (preferredColor: 'WHITE' | 'BLACK' | 'ANY' = 'ANY', timeControl: string = 'rapid') => {
    try {
      const response = await api.post('/matchmaking/', {
        preferred_color: preferredColor,
        time_control: timeControl
      });
      return response.data;
    } catch (error) {
      console.error('Failed to join queue:', error);
      throw error;
    }
  },

  // Sair da fila de jogo
  leaveQueue: async () => {
    try {
      await api.post('/matchmaking/');
    } catch (error) {
      console.error('Failed to leave queue:', error);
      throw error;
    }
  },

  // Verificar estado da partida
  checkMatchStatus: async () => {
    try {
      const response = await api.get('/matchmaking/');
      return response.data;
    } catch (error) {
      console.error('Failed to check match status:', error);
      throw error;
    }
  },
};

export default api;
