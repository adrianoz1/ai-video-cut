#!/bin/bash
#
# Script completo para processar vídeo do YouTube
#
# Este script baixa um vídeo do YouTube, extrai áudio, transcreve com Whisper API,
# gera legendas SRT, encontra highlights usando GPT, adiciona legendas e converte
# para formato vertical, e finalmente gera clips dos highlights.
#
# Uso:
#   ./process_video.sh <youtube_url> [openai_api_key]
#
# Ou defina OPENAI_API_KEY como variável de ambiente.

set -euo pipefail  # Para na primeira erro, trata variáveis não definidas e pipes

# Cores para output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Constantes
readonly SCRIPT_NAME="$(basename "$0")"
readonly REQUIRED_COMMANDS=("yt-dlp" "ffmpeg" "ffprobe" "python3" "jq")

# Funções auxiliares
print_error() {
    echo -e "${RED}Erro: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_info() {
    echo -e "${BLUE}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Verificar argumentos
if [ $# -lt 1 ]; then
    print_error "URL do YouTube não fornecida"
    echo "Uso: $SCRIPT_NAME <youtube_url> [openai_api_key]"
    echo ""
    echo "Ou defina OPENAI_API_KEY como variável de ambiente"
    exit 1
fi

readonly YOUTUBE_URL="$1"
readonly OPENAI_API_KEY="${2:-${OPENAI_API_KEY:-}}"

if [ -z "$OPENAI_API_KEY" ]; then
    print_error "OPENAI_API_KEY não encontrada"
    echo "Defina como segundo argumento ou variável de ambiente"
    exit 1
fi

# Diretório do script
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly WORK_DIR="${SCRIPT_DIR}/video_processing_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORK_DIR"

print_header "Processamento de Vídeo do YouTube"
echo -e "📁 Diretório de trabalho: ${WORK_DIR}"
echo -e "🔗 URL: ${YOUTUBE_URL}"
echo ""

# Função para verificar se comando existe
check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        print_error "$cmd não encontrado"
        echo "Instale com: brew install $cmd"
        exit 1
    fi
}

# Verificar dependências
print_warning "🔍 Verificando dependências..."
for cmd in "${REQUIRED_COMMANDS[@]}"; do
    check_command "$cmd"
done
print_success "✅ Todas as dependências encontradas"
echo ""

# Função para executar comando e tratar erros
run_step() {
    local step_num="$1"
    local step_name="$2"
    local cmd="$3"
    
    print_info "[$step_num/7] $step_name"
    if eval "$cmd"; then
        print_success "✅ $step_name concluído"
        echo ""
        return 0
    else
        print_error "$step_name falhou"
        exit 1
    fi
}

# 1️⃣ Baixar vídeo
cd "$WORK_DIR"
run_step "1" "📥 Baixando vídeo do YouTube" \
    "yt-dlp -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' -o 'video.%(ext)s' '$YOUTUBE_URL'"

VIDEO_FILE=$(find . -maxdepth 1 -name 'video.*' -type f | head -1)
if [ -z "$VIDEO_FILE" ]; then
    print_error "Vídeo não foi baixado"
    exit 1
fi
VIDEO_FILE=$(basename "$VIDEO_FILE")
print_success "✅ Vídeo baixado: $VIDEO_FILE"
echo ""

# 2️⃣ Extrair áudio
run_step "2" "🎵 Extraindo áudio do vídeo" \
    "ffmpeg -y -i '$VIDEO_FILE' -vn -acodec libmp3lame -q:a 2 'audio.mp3'"

# 3️⃣ Transcrever áudio
run_step "3" "🗣️  Transcrevendo áudio com Whisper API" \
    "curl -s -f https://api.openai.com/v1/audio/transcriptions \
        -H 'Authorization: Bearer $OPENAI_API_KEY' \
        -F 'file=@audio.mp3' \
        -F 'model=whisper-1' \
        -F 'response_format=verbose_json' \
        -o 'transcript.json'"

if [ ! -s transcript.json ]; then
    print_error "Transcrição vazia"
    exit 1
fi

# 4️⃣ Gerar subtítulos SRT
run_step "4" "📝 Gerando arquivo SRT" \
    "python3 '${SCRIPT_DIR}/generate_srt.py' transcript.json subtitles.srt"

# 5️⃣ Encontrar highlights
run_step "5" "🔍 Buscando melhores momentos" \
    "python3 '${SCRIPT_DIR}/find_highlights.py' transcript.json highlights.json '$OPENAI_API_KEY'"

# 6️⃣ Adicionar legendas e converter para vertical
run_step "6" "🎬 Adicionando legendas e convertendo para vertical" \
    "python3 '${SCRIPT_DIR}/add_subtitles.py' '$VIDEO_FILE' subtitles.srt video_with_subs.mp4"

# 7️⃣ Gerar clips
run_step "7" "✂️  Gerando clips dos highlights" \
    "mkdir -p clips && python3 '${SCRIPT_DIR}/generate_clips.py' video_with_subs.mp4 highlights.json clips"

# Resumo final
print_header "✅ Processamento concluído!"
echo "📁 Arquivos gerados em: $WORK_DIR"
echo ""
echo "📄 Arquivos principais:"
echo "  - $VIDEO_FILE (vídeo original)"
echo "  - video_with_subs.mp4 (vídeo com legendas, vertical)"
echo "  - subtitles.srt (legendas)"
echo "  - transcript.json (transcrição completa)"
echo "  - highlights.json (melhores momentos)"
echo ""

if [ -d clips ] && [ "$(ls -A clips 2>/dev/null)" ]; then
    echo "🎬 Clips gerados:"
    ls -lh clips/ 2>/dev/null | tail -n +2 | awk '{print "  - " $9 " (" $5 ")"}'
    echo ""
fi

print_warning "💡 Dica: Os clips estão prontos para uso!"
