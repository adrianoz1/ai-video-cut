# AI VideoCut - Processador Automático de Vídeos do YouTube

Ferramenta completa para processar vídeos do YouTube, gerar legendas automáticas, identificar highlights virais e criar clips otimizados para TikTok, Reels e YouTube Shorts.

## 📋 Funcionalidades

- 📥 **Download automático** de vídeos do YouTube
- 🗣️ **Transcrição automática** usando Whisper API da OpenAI
- 📝 **Geração de legendas** em formato SRT
- 🔍 **Identificação de highlights** usando GPT-4o-mini para encontrar os melhores momentos
- 🎬 **Adição de legendas** estilo TikTok (palavras aparecendo uma a uma)
- 📱 **Conversão para formato vertical** (9:16) otimizado para redes sociais
- ✂️ **Geração automática de clips** dos highlights identificados

## 🛠️ Dependências

### Ferramentas Necessárias

O projeto requer as seguintes ferramentas instaladas no sistema:

#### macOS (usando Homebrew)

```bash
# Instalar todas as dependências de uma vez
brew install yt-dlp ffmpeg python3 jq
```

#### Linux (Ubuntu/Debian)

```bash
# Atualizar pacotes
sudo apt-get update

# Instalar dependências
sudo apt-get install -y yt-dlp ffmpeg python3 jq curl
```

#### Windows (usando Chocolatey)

```powershell
choco install yt-dlp ffmpeg python3 jq
```

### Verificação de Instalação

Verifique se todas as dependências estão instaladas:

```bash
# Verificar comandos
yt-dlp --version
ffmpeg -version
ffprobe -version
python3 --version
jq --version
```

### APIs Necessárias

- **OpenAI API Key**: Necessária para:
  - Transcrição de áudio (Whisper API)
  - Identificação de highlights (GPT-4o-mini)

  Obtenha sua chave em: https://platform.openai.com/api-keys

## ⚙️ Configuração

### 1. Configurar OpenAI API Key

Você pode configurar a API key de duas formas:

#### Opção 1: Variável de Ambiente (Recomendado)

**macOS/Linux:**
```bash
export OPENAI_API_KEY="sua-chave-api-aqui"
```

Para tornar permanente, adicione ao seu `~/.bashrc` ou `~/.zshrc`:
```bash
echo 'export OPENAI_API_KEY="sua-chave-api-aqui"' >> ~/.zshrc
source ~/.zshrc
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sua-chave-api-aqui"
```

#### Opção 2: Passar como Argumento

A API key pode ser passada diretamente como segundo argumento ao executar o script.

### 2. Dar Permissão de Execução ao Script

```bash
chmod +x process_video.sh
```

## 🚀 Como Usar

### Uso Básico

```bash
# Com variável de ambiente configurada
./process_video.sh "https://www.youtube.com/watch?v=VIDEO_ID"

# Passando API key como argumento
./process_video.sh "https://www.youtube.com/watch?v=VIDEO_ID" "sua-chave-api"
```

### Exemplos Práticos

#### Exemplo 1: Processar um vídeo completo

```bash
./process_video.sh "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

#### Exemplo 2: Com API key explícita

```bash
./process_video.sh \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  "sk-proj-xxxxxxxxxxxxxxxxxxxxx"
```

### Usando Scripts Individuais

Você também pode usar os scripts Python individualmente:

#### Gerar legendas SRT

```bash
python3 generate_srt.py transcript.json subtitles.srt
```

#### Encontrar highlights

```bash
python3 find_highlights.py transcript.json highlights.json "$OPENAI_API_KEY"
```

#### Adicionar legendas ao vídeo

```bash
python3 add_subtitles.py video.mp4 subtitles.srt video_with_subs.mp4
```

#### Gerar clips

```bash
python3 generate_clips.py video_with_subs.mp4 highlights.json ./clips
```

## 📁 Estrutura do Projeto

```
videocut/
├── process_video.sh      # Script principal (orquestra todo o processo)
├── generate_srt.py       # Gera arquivo SRT a partir da transcrição
├── find_highlights.py    # Identifica highlights usando GPT
├── add_subtitles.py      # Adiciona legendas e converte para vertical
├── generate_clips.py     # Gera clips dos highlights
└── README.md            # Este arquivo
```

## 📂 Arquivos Gerados

Após a execução, o script cria um diretório com timestamp contendo:

```
video_processing_YYYYMMDD_HHMMSS/
├── video.*               # Vídeo original baixado
├── audio.mp3             # Áudio extraído
├── transcript.json       # Transcrição completa em JSON
├── subtitles.srt         # Arquivo de legendas SRT
├── highlights.json       # JSON com highlights identificados
├── video_with_subs.mp4   # Vídeo com legendas em formato vertical (9:16)
└── clips/                # Pasta com os clips gerados
    ├── clip_01_30s_90s.mp4
    ├── clip_02_120s_210s.mp4
    └── ...
```

## 🔍 Formato dos Arquivos

### transcript.json

```json
{
  "text": "Texto completo da transcrição...",
  "segments": [
    {
      "start": 0.0,
      "end": 5.5,
      "text": "Primeiro segmento de texto"
    }
  ]
}
```

### highlights.json

```json
[
  {
    "start": 30.0,
    "end": 90.0,
    "duration": 60,
    "reason": "Explicação do potencial viral deste segmento",
    "transcript": "Texto do segmento..."
  }
]
```

## ⚠️ Troubleshooting

### Erro: "yt-dlp não encontrado"

```bash
# macOS
brew install yt-dlp

# Linux
sudo apt-get install yt-dlp
```

### Erro: "ffmpeg não encontrado"

```bash
# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

### Erro: "OPENAI_API_KEY não encontrada"

Certifique-se de que a variável de ambiente está configurada:

```bash
echo $OPENAI_API_KEY
```

Ou passe a chave como segundo argumento.

### Erro ao baixar vídeo

- Verifique se a URL do YouTube está correta
- Alguns vídeos podem ter restrições de download
- Tente atualizar o yt-dlp: `pip install --upgrade yt-dlp`

### Erro na transcrição

- Verifique se sua API key da OpenAI está válida
- Confirme que você tem créditos disponíveis na conta OpenAI
- Verifique a conexão com a internet

### Vídeo muito grande

Para vídeos muito longos, o processamento pode demorar. O script tem timeout de 20 minutos por etapa. Considere processar vídeos menores ou aumentar o timeout no código.

## 📝 Requisitos do Sistema

- **Python**: 3.7 ou superior
- **Espaço em disco**: Variável (depende do tamanho dos vídeos)
- **RAM**: Mínimo 4GB recomendado
- **Conexão**: Internet estável para download e APIs

## 🔐 Segurança

⚠️ **Importante**: Nunca compartilhe sua API key da OpenAI publicamente. Use variáveis de ambiente ou arquivos de configuração seguros.

## 📄 Licença

Este projeto é fornecido como está, sem garantias.

## 🤝 Contribuindo

Sugestões e melhorias são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## 📚 Recursos Adicionais

- [Documentação yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [Documentação FFmpeg](https://ffmpeg.org/documentation.html)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Whisper API](https://platform.openai.com/docs/guides/speech-to-text)

---

**Desenvolvido com ❤️ para criadores de conteúdo**
