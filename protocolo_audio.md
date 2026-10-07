# Protocolo de Áudio Alfa + Theta + Gamma

Sessão estéreo de **15 minutos**.

## Protocolo

- **0:00–5:00:** 10 Hz — Alfa
- **5:00–11:00:** 4,5 Hz — Theta
- **11:00–12:00:** transição gradual de 4,5 Hz para 40 Hz
- **12:00–15:00:** 40 Hz — Gamma

## Configuração do sinal

- **Portadora:** 288 Hz
- **Canal esquerdo:** 288 Hz
- **Canal direito:** 288 Hz + frequência-alvo instantânea
- **Modulação:** a mesma frequência-alvo modula suavemente a amplitude dos dois canais
- **Duração total:** 900 segundos
- **Formato:** WAV estéreo, PCM 16-bit, 8 kHz

O aplicativo mantém um único arquivo de áudio no repositório:

`audio/parceria_ceitec_ecomcs.wav`

Além do WAV, o aplicativo mantém `audio/protocolo_version.txt`, um pequeno marcador técnico. Quando o protocolo muda, o hash muda automaticamente; na primeira execução da nova versão, o WAV é regenerado e sobrescrito. Nas execuções seguintes, o arquivo existente é reutilizado.

> As frequências acima descrevem o estímulo auditivo gerado pelo aplicativo. Não constituem garantia de um estado cerebral específico ou de efeitos externos.
