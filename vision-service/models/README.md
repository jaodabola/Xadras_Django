# XADRAS Vision Service - Diretório do Modelo YOLO

Coloca aqui o teu modelo YOLO treinado.

## Modelo Esperado

Ficheiro: `chess_pieces.pt`

### Classes (por ordem):
0. vazio (empty)
1. black-bishop (bispo preto)
2. black-king (rei preto)
3. black-knight (cavalo preto)
4. black-pawn (peão preto)
5. black-queen (rainha preta)
6. black-rook (torre preta)
7. white-bishop (bispo branco)
8. white-king (rei branco)
9. white-knight (cavalo branco)
10. white-pawn (peão branco)
11. white-queen (rainha branca)
12. white-rook (torre branca)

## Utilização

1. Copia o teu modelo treinado para este diretório
2. Renomeia-o para `chess_pieces.pt` (ou atualiza MODEL_PATH nas variáveis de ambiente)
3. Executa o serviço de visão: `python main.py`
