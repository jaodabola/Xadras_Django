---
metaLinks:
  alternates:
    - https://app.gitbook.com/s/M9ty6FYa3j98VSBHF9LN/
---

# XADRAS - Plataforma de Xadrez com Visão Computacional

[![API Docs](https://img.shields.io/badge/API-Documenta%C3%A7%C3%A3o-blue)](https://docs.xadras.com)&#x20;

XADRAS é uma plataforma inovadora que combina reconhecimento de tabuleiros físicos de xadrez com jogos online em tempo real.

## 🎯 Funcionalidades

* **🎮 Jogos Online** - Cria e joga partidas de xadrez em tempo real
* **🏆 Torneios** - Sistema Swiss com classificações e emparelhamentos automáticos
* **📷 Visão AI** - Deteção de peças via câmaras e marcadores ArUco
* **⚡ Matchmaking** - Emparelhamento automático baseado em rating ELO
* **👤 Contas** - Registo completo ou contas de convidado

## 📁 Estrutura do Projeto

```
xadras/
├── backend/          # API Django REST
│   └── xadras/
│       ├── accounts/      # Gestão de utilizadores
│       ├── game/          # Lógica de jogos
│       ├── matchmaking/   # Sistema de emparelhamento
│       ├── tournaments/   # Gestão de torneios
│       └── cameras/       # Gestão de câmaras e streams
├── frontend/         # Interface React
├── vision-service/   # Serviço de visão computacional
└── monitoring/       # Monitorização e métricas
```

## 🚀 Início Rápido

### Backend (Django)

```bash
cd backend/xadras
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

### Vision Service

```bash
cd vision-service
pip install -r requirements.txt
python main.py --debug
```

## 🔑 Autenticação

A API usa autenticação por token:

```bash
# Obter token
curl -X POST http://localhost:8000/api/token/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "utilizador", "password": "password"}'

# Usar token
curl http://localhost:8000/api/game/ \
  -H "Authorization: Token <o-teu-token>"
```

## 📡 WebSocket

Comunicação em tempo real para jogos:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/game/<game_id>/?token=<auth_token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'move') {
    console.log('Jogada:', data.move_san);
  }
};
```

## 📚 Documentação da API

A documentação completa da API está disponível em:

* **GitBook**: [https://app.gitbook.com/o/1ePv0zfiw298i7k4f0YD/s/Wff56F3jruJVj0mZxpM7/](https://app.gitbook.com/o/1ePv0zfiw298i7k4f0YD/s/Wff56F3jruJVj0mZxpM7/)
* **OpenAPI Spec**: [openapi.yaml](openapi.yaml)

## 🏗️ Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │◀────│   Vision    │
│   (React)   │     │  (Django)   │     │  Service    │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                    │
                    ┌──────▼──────┐      ┌──────▼──────┐
                    │  PostgreSQL │      │   Câmara    │
                    │   + Redis   │      │   + YOLO    │
                    └─────────────┘      └─────────────┘
```

