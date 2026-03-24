# XADRAS Vision Service

Serviço de visão computacional para deteção do estado do tabuleiro de xadrez usando marcadores ArUco e YOLO.

## Início Rápido

### 1. Instalar Dependências

```bash
cd vision-service
pip install -r requirements.txt
```

### 2. Adicionar o Modelo YOLO

Coloca o teu modelo treinado em: `models/chess_pieces.pt`

### 3. Imprimir Marcadores ArUco

Imprime os 4 marcadores e coloca nos cantos do tabuleiro:

| ID do Marcador | Posição | Canto |
|----------------|---------|-------|
| 0 | Cima-Esquerda | a8 |
| 1 | Cima-Direita | h8 |
| 2 | Baixo-Direita | h1 |
| 3 | Baixo-Esquerda | a1 |

Gera marcadores em: https://chev.me/arucogen/
- Dicionário: 4x4 (50 marcadores)
- IDs dos Marcadores: 0, 1, 2, 3
- Tamanho: 30-50mm recomendado

### 4. Executar o Serviço

```bash
# Com visualização de debug
python main.py --debug

# Modo de teste (sem backend)
python main.py --debug --test

# Modo de produção
python main.py
```

## Configuração

Definir via variáveis de ambiente:

| Variável | Valor Padrão | Descrição |
|----------|--------------|-----------|
| `BACKEND_WS_URL` | `ws://localhost:8000/ws/vision/` | Endpoint WebSocket |
| `CAMERA_TOKEN` | (obrigatório) | Token de autenticação da câmara |
| `CAMERA_ID` | (obrigatório) | ID da câmara registada |
| `USE_PICAMERA` | `true` | Usar RPi AI Camera (false para USB) |
| `CAMERA_INDEX` | `0` | Índice do dispositivo de câmara |
| `MODEL_PATH` | `models/chess_pieces.pt` | Caminho para o modelo YOLO |
| `CONFIDENCE_THRESHOLD` | `0.5` | Confiança mínima de deteção |
| `DEBUG` | `false` | Ativar modo debug |

## Arquitetura

```
Câmara → Deteção ArUco → Warp do Tabuleiro → Peças YOLO → FEN → WebSocket
```

### Componentes

| Ficheiro | Função |
|----------|--------|
| `main.py` | Ponto de entrada e orquestração |
| `src/camera.py` | Interface da câmara (RPi + USB) |
| `src/aruco_detector.py` | Deteção de marcadores ArUco |
| `src/board_warper.py` | Transformação de perspetiva |
| `src/piece_detector.py` | Deteção de peças com YOLO |
| `src/fen_generator.py` | Geração de strings FEN |
| `src/websocket_client.py` | Comunicação com o backend |
| `src/config.py` | Configuração |

## Configuração no Raspberry Pi

### Instalar picamera2 (apenas RPi)

```bash
sudo apt install -y python3-picamera2
```

### Executar no RPi

```bash
export CAMERA_TOKEN="o-teu-token"
export CAMERA_ID="o-id-da-tua-camara"
export BACKEND_WS_URL="ws://o-teu-servidor:8000/ws/vision/"
python main.py
```

## Posicionamento dos Marcadores ArUco

```
┌─────────────────────────────────────────┐
│  [ID:0]                        [ID:1]   │
│    ■                              ■     │
│                                         │
│           Tabuleiro de Xadrez           │
│                                         │
│    ■                              ■     │
│  [ID:3]                        [ID:2]   │
└─────────────────────────────────────────┘
```

O serviço funciona com 2-4 marcadores visíveis (3+ recomendado).
