# ♟️ XADRAS Backend - API REST

## 🎯 Funcionalidades Principais

*   🔐 **Autenticação Premium** - Registo, login e gestão segura de sessões via JWT/Djoser.
*   ⚔️ **Jogos em Tempo Real** - Sincronização de baixa latência através de WebSockets (Django Channels).
*   🤝 **Matchmaking Inteligente** - Fila de espera dinâmica com emparelhamento baseado no rating ELO.
*   🏆 **Gestão de Torneios** - Suporte completo a sistemas **Swiss**, **Round Robin** e **Eliminação Única**.
*   📸 **Xadras Vision Integration** - Endpoint dedicado para receber estados de tabuleiros físicos detetados por telemóvel.
*   👤 **Sistema de Convidados** - Permite a entrada imediata de jogadores sem necessidade de registo inicial.

---

## 📋 Requisitos do Sistema

*   **Linguagem**: Python 3.11+
*   **Base de Dados**: 
    *   **Desenvolvimento**: SQLite 3 (configurado por defeito)
    *   **Produção**: PostgreSQL 14+ (recomendado)
*   **Cache & Mensagens**: Redis 6+ (Obrigatório para WebSockets e Rate Limiting)
*   **Infraestrutura**: Docker & Docker Compose (Recomendado para deploy)

---

## 🐳 Início Rápido com Docker

```bash
# 1. Clonar o repositório
git clone https://github.com/jaodabola/Xadras.git
cd Xadras

# 2. Configurar variáveis de ambiente
cp .env.example .env

# 3. Levantar a infraestrutura
docker-compose up -d --build
```

A API estará disponível em: `http://localhost:8000`

---

## 💻 Configuração Local (Desenvolvimento)

### 1. Preparação do Ambiente
```bash
cd backend/xadras
python -m venv venv

# Ativar ambiente (Windows)
.\venv\Scripts\activate
# Ativar ambiente (Linux/MacOS)
source venv/bin/activate
```

### 2. Instalação e Migração
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

### 3. Execução
```bash
# Iniciar servidor de desenvolvimento (Daphne/Django)
python manage.py runserver 0.0.0.0:8000
```
*Nota: Certifique-se de que o **Redis** está a correr localmente para suportar WebSockets.*

---

## 📁 Arquitetura do Projeto

```text
backend/xadras/
├── accounts/       # Gestão de utilizadores, ratings ELO e perfis
├── game/           # Core: Lógica de jogo, movimentos e Transmissão FEN
├── matchmaking/    # Algoritmos de fila e emparelhamento asíncrono
├── tournaments/    # Engine de torneios (Swiss, Standings, Pairing)
└── xadras/         # Configurações globais, Middleware e ASGI
```

---

## 📡 Visão Geral da API

### Principais Endpoints

| Área | Método | Endpoint | Descrição |
| :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/token/login/` | Obtenção de Token |
| **Accounts** | `POST` | `/api/accounts/guest/` | Criação de utilizador temporário |
| **Game** | `POST` | `/api/game/live-board/fen/` | **Xadras Vision**: Envio de FEN via Mobile |
| **Matchmaking** | `POST` | `/api/matchmaking/` | Entrada/Saída da fila de espera |
| **Tournaments** | `GET` | `/api/tournaments/` | Listagem e gestão de torneios |

> [!TIP]
> A documentação completa e interativa dos endpoints pode ser encontrada via **Swagger/OpenAPI** em `/api/docs/` (se habilitado) ou no ficheiro [openapi.yaml](../openapi.yaml).

---

## 🔌 Protocolo WebSocket

A comunicação em tempo real é feita através do path:
`ws://<host>/ws/game/<game_id>/?token=<auth_token>`

**Exemplo de Mensagem de Jogada (Send):**
```json
{
  "type": "move",
  "move_san": "Nf3",
  "fen_after": "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1"
}
```

---

## 🧪 Qualidade de Código

Para garantir a integridade do sistema, execute a suite de testes:
```bash
python manage.py test
```

---

## 📚 Documentação Adicional

*   [Guia de Arquitetura Superior](../DOCS_ARCHITECTURE.md)
*   [Especificação OpenAPI](../openapi.yaml)
*   [Portal GitBook](https://app.gitbook.com/o/1ePv0zfiw298i7k4f0YD/s/Wff56F3jruJVj0mZxpM7/)

---
*XADRAS - Transforming Chess with AI Vision. 2026.*
