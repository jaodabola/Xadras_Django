# XADRAS Frontend - Interface React

Interface moderna e responsiva para a plataforma de xadrez XADRAS, construída com React, TypeScript e Vite.

## 🎯 Funcionalidades

* **Tabuleiro Interativo** - Arrastar e largar peças com validação de jogadas
* **Jogos em Tempo Real** - Sincronização via WebSocket
* **Histórico de Jogadas** - Navegação por jogadas anteriores
* **Peças Capturadas** - Visualização das peças fora do jogo
* **Virar Tabuleiro** - Jogar como brancas ou pretas
* **Modo Ecrã Inteiro** - Experiência imersiva
* **Design Responsivo** - Funciona em desktop e mobile

## 📋 Requisitos

* Node.js 18+
* npm 9+ ou yarn
* Docker & Docker Compose (opcional)

## 🐳 Início Rápido com Docker

```bash
# Na raiz do projeto
docker-compose up -d frontend

# A aplicação estará disponível em:
# http://localhost:5173
```

## 💻 Desenvolvimento Local

### 1. Instalar Dependências

```bash
cd frontend
npm install
```

### 2. Configurar Ambiente

```bash
# Criar ficheiro .env
cp .env.example .env
```

Editar `.env`:

```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### 3. Executar em Desenvolvimento

```bash
npm run dev
```

A aplicação estará disponível em: `http://localhost:5173`

## 📁 Estrutura do Projeto

```
frontend/
├── public/                 # Ficheiros estáticos
└── src/
    ├── assets/            # Imagens, fontes, ícones
    ├── components/        # Componentes reutilizáveis
    │   ├── ChessBoard/    # Tabuleiro de xadrez
    │   ├── CapturedPieces/# Peças capturadas
    │   ├── Game/          # Componente principal do jogo
    │   ├── GameControls/  # Controlos do jogo
    │   └── MoveHistory/   # Histórico de jogadas
    ├── hooks/             # Custom hooks
    │   ├── useGame.ts     # Lógica do jogo
    │   └── useWebSocket.ts# Conexão WebSocket
    ├── pages/             # Páginas da aplicação
    │   ├── Home/          # Página inicial
    │   ├── Game/          # Página do jogo
    │   ├── Profile/       # Perfil do utilizador
    │   └── Tournaments/   # Torneios
    ├── services/          # Serviços de API
    │   ├── api.ts         # Cliente HTTP
    │   └── websocket.ts   # Cliente WebSocket
    ├── types/             # Definições TypeScript
    ├── App.tsx            # Componente raiz
    └── main.tsx           # Ponto de entrada
```

## 🛠️ Scripts Disponíveis

| Comando                 | Descrição                          |
| ----------------------- | ---------------------------------- |
| `npm run dev`           | Inicia servidor de desenvolvimento |
| `npm run build`         | Compila para produção              |
| `npm run preview`       | Pré-visualiza build de produção    |
| `npm run lint`          | Verifica erros de código (ESLint)  |
| `npm run test`          | Executa testes                     |
| `npm run test:coverage` | Testes com cobertura               |

## 🎨 Tecnologias

| Tecnologia                                     | Utilização                   |
| ---------------------------------------------- | ---------------------------- |
| [React 18](https://react.dev/)                 | Biblioteca UI                |
| [TypeScript](https://www.typescriptlang.org/)  | Tipagem estática             |
| [Vite](https://vitejs.dev/)                    | Build tool e dev server      |
| [chess.js](https://github.com/jhlywa/chess.js) | Validação de jogadas         |
| [Tailwind CSS](https://tailwindcss.com/)       | Estilização                  |
| [React Query](https://tanstack.com/query)      | Gestão de estado do servidor |
| [React Router](https://reactrouter.com/)       | Navegação                    |

## 🔌 Integração com Backend

### Autenticação

```typescript
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

// Adicionar token a todos os pedidos
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});
```

### WebSocket

```typescript
// hooks/useWebSocket.ts
export function useGameWebSocket(gameId: string) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const token = localStorage.getItem('token');
  
  useEffect(() => {
    const ws = new WebSocket(
      `${import.meta.env.VITE_WS_URL}/game/${gameId}/?token=${token}`
    );
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Processar eventos...
    };
    
    setSocket(ws);
    return () => ws.close();
  }, [gameId, token]);
  
  return socket;
}
```

## 🧪 Testes

```bash
# Executar testes
npm run test

# Modo watch
npm run test:watch

# Com cobertura
npm run test:coverage
```

## 📦 Build de Produção

```bash
# Compilar
npm run build

# O output estará em dist/
```

### Deploy com Docker

```dockerfile
# Dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

## 🔧 Variáveis de Ambiente

| Variável       | Descrição       | Exemplo                     |
| -------------- | --------------- | --------------------------- |
| `VITE_API_URL` | URL da API REST | `http://localhost:8000/api` |
| `VITE_WS_URL`  | URL WebSocket   | `ws://localhost:8000/ws`    |

## 📱 Responsividade

A aplicação é totalmente responsiva:

| Dispositivo | Breakpoint     |
| ----------- | -------------- |
| Mobile      | < 640px        |
| Tablet      | 640px - 1024px |
| Desktop     | > 1024px       |

##
