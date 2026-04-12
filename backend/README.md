# XADRAS Backend - API REST

API REST para a plataforma de xadrez XADRAS, construída com Django, Django REST Framework e WebSockets para jogabilidade em tempo real.

## 🎯 Funcionalidades

* **Autenticação** - Registo, login e gestão de tokens (Djoser)
* **Jogos em Tempo Real** - WebSockets para sincronização de jogadas
* **Sistema de Matchmaking** - Emparelhamento automático baseado em ELO
* **Torneios** - Sistema Swiss com classificações e emparelhamentos
* **Visão AI** - Integração com câmaras para deteção de tabuleiros físicos
* **Modo Convidado** - Jogadores não registados podem jogar

## 📋 Requisitos

* Python 3.10+
* PostgreSQL 14+
* Redis 6+
* Docker & Docker Compose (recomendado)

## 🐳 Início Rápido com Docker

### 1. Clonar e Configurar

```bash
git clone https://github.com/jaodabola/Xadras.git
cd Xadras
```

### 2. Criar Ficheiro de Ambiente

```bash
cp .env.example .env
# Editar .env com as tuas configurações
```

### 3. Executar com Docker Compose

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f backend

# Parar serviços
docker-compose down
```

A API estará disponível em: `http://localhost:8000`

## 💻 Desenvolvimento Local (Sem Docker)

### 1. Ambiente Virtual

```bash
cd backend/xadras

# Linux/MacOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
```

### 2. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar Base de Dados

```bash
python manage.py migrate
python manage.py createsuperuser  # Opcional
```

### 4. Iniciar Servidores

```bash
# Terminal 1 - Django
python manage.py runserver

# Terminal 2 - Redis (necessário para WebSockets)
redis-server
```

## 📁 Estrutura do Projeto

```
backend/
└── xadras/
    ├── accounts/       # Gestão de utilizadores e autenticação
    ├── game/           # Lógica de jogos e WebSocket consumers
    ├── matchmaking/    # Sistema de emparelhamento
    ├── tournaments/    # Gestão de torneios Swiss
    └── xadras/         # Configurações do projeto
```

## 📡 Endpoints da API

### Autenticação

| Método | Endpoint             | Descrição           |
| ------ | -------------------- | ------------------- |
| `POST` | `/api/users/`        | Registar utilizador |
| `POST` | `/api/token/login/`  | Obter token         |
| `POST` | `/api/token/logout/` | Invalidar token     |
| `GET`  | `/api/users/me/`     | Utilizador atual    |

### Contas

| Método | Endpoint                 | Descrição             |
| ------ | ------------------------ | --------------------- |
| `POST` | `/api/accounts/guest/`   | Criar conta convidado |
| `GET`  | `/api/accounts/profile/` | Perfil do utilizador  |
| `GET`  | `/api/accounts/stats/`   | Estatísticas          |

### Jogos

| Método | Endpoint               | Descrição      |
| ------ | ---------------------- | -------------- |
| `GET`  | `/api/game/`           | Listar jogos   |
| `POST` | `/api/game/`           | Criar jogo     |
| `POST` | `/api/game/{id}/join/` | Entrar no jogo |
| `POST` | `/api/game/{id}/move/` | Fazer jogada   |
| `POST` | `/api/game/{id}/end/`  | Terminar jogo  |

### Matchmaking

| Método | Endpoint                  | Descrição      |
| ------ | ------------------------- | -------------- |
| `POST` | `/api/matchmaking/join/`  | Entrar na fila |
| `POST` | `/api/matchmaking/leave/` | Sair da fila   |
| `GET`  | `/api/matchmaking/`       | Estado da fila |

### Torneios

| Método | Endpoint                           | Descrição       |
| ------ | ---------------------------------- | --------------- |
| `GET`  | `/api/tournaments/`                | Listar torneios |
| `POST` | `/api/tournaments/`                | Criar torneio   |
| `POST` | `/api/tournaments/{id}/join/`      | Inscrever-se    |
| `POST` | `/api/tournaments/{id}/start/`     | Iniciar torneio |
| `GET`  | `/api/tournaments/{id}/standings/` | Classificação   |

## 🔌 WebSocket

```javascript
// Conectar ao jogo
const ws = new WebSocket('ws://localhost:8000/ws/game/<game_id>/?token=<auth_token>');

// Eventos recebidos
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'move':
      console.log('Jogada:', data.move_san);
      break;
    case 'board_update':
      console.log('FEN:', data.fen);
      break;
    case 'game_end':
      console.log('Resultado:', data.result);
      break;
  }
};

// Enviar jogada
ws.send(JSON.stringify({
  type: 'move',
  move_san: 'e4',
  fen_after: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'
}));
```

## 🔧 Variáveis de Ambiente

```env
# Django
SECRET_KEY=chave-secreta-segura
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de Dados
DATABASE_URL=postgres://user:password@localhost:5432/xadras

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

## 🧪 Testes

```bash
# Executar todos os testes
python manage.py test

# Com cobertura
coverage run manage.py test
coverage report
```

## 📚 Documentação

* [OpenAPI Spec](../openapi.yaml) - Especificação completa da API
* [GitBook Documentação](https://app.gitbook.com/o/1ePv0zfiw298i7k4f0YD/s/Wff56F3jruJVj0mZxpM7/) - Documentação interativa

