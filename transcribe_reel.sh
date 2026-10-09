#!/bin/bash
#
# Transcreve o roteiro falado de um Reel do Instagram.
#
# Baixa o vídeo, extrai o áudio e envia para a Whisper API.
# O texto contínuo fica em roteiro.txt; os timestamps ficam em transcript.json.
#
# Uso:
#   ./transcribe_reel.sh <url_do_reel> [openai_api_key]
#
# Ou defina OPENAI_API_KEY como variável de ambiente.
#
# O Instagram exige sessão logada. O script usa cookies.txt na raiz do projeto
# ou, na ausência dele, os cookies do navegador (YT_DLP_COOKIES_BROWSER, padrão: chrome).

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REQUIRED_COMMANDS=("yt-dlp" "ffmpeg" "ffprobe" "jq" "curl")
readonly WHISPER_MAX_BYTES=$((25 * 1024 * 1024))

print_error() { echo -e "${RED}Erro: $1${NC}" >&2; }
print_success() { echo -e "${GREEN}$1${NC}"; }
print_info() { echo -e "${BLUE}$1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

if [ $# -lt 1 ]; then
    print_error "URL do Reel não fornecida"
    echo "Uso: $SCRIPT_NAME <url_do_reel> [openai_api_key]"
    echo ""
    echo "Exemplo:"
    echo "  $SCRIPT_NAME \"https://www.instagram.com/reel/CODIGO/\""
    exit 1
fi

readonly REEL_URL="$1"
readonly OPENAI_API_KEY="${2:-${OPENAI_API_KEY:-}}"

if [[ ! "$REEL_URL" =~ ^https?://([a-zA-Z0-9-]+\.)?instagram\.com/(reel|reels|p|tv)/[^/?#]+ ]]; then
    print_error "URL inválida. Passe o link de um Reel, por exemplo:"
    echo "  https://www.instagram.com/reel/CODIGO/"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    print_error "OPENAI_API_KEY não encontrada"
    echo "Defina como segundo argumento ou variável de ambiente"
    exit 1
fi

check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        print_error "$cmd não encontrado"
        echo "Instale com: brew install $cmd"
        exit 1
    fi
}

print_warning "🔍 Verificando dependências..."
for cmd in "${REQUIRED_COMMANDS[@]}"; do
    check_command "$cmd"
done
print_success "✅ Todas as dependências encontradas"

readonly WORK_DIR="${SCRIPT_DIR}/reel_transcription_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORK_DIR"

print_header "Transcrição de Reel do Instagram"
echo -e "📁 Diretório de trabalho: ${WORK_DIR}"
echo -e "🔗 URL: ${REEL_URL}"
echo ""

# Cookies e proxy seguem o mesmo critério de download_video.sh
COOKIES_OPT=""
if [ -f "${SCRIPT_DIR}/cookies.txt" ]; then
    COOKIES_OPT="--cookies ${SCRIPT_DIR}/cookies.txt"
    print_info "   Cookies: cookies.txt"
else
    BROWSER="${YT_DLP_COOKIES_BROWSER:-chrome}"
    COOKIES_OPT="--cookies-from-browser $BROWSER"
    print_info "   Cookies: navegador $BROWSER"
fi

PROXY_OPT=""
PROXIES_FILE="${SCRIPT_DIR}/proxies.txt"
if [ -f "$PROXIES_FILE" ]; then
    PROXIES=($(grep -v '^[[:space:]]*#' "$PROXIES_FILE" | grep -v '^[[:space:]]*$' || true))
    if [ ${#PROXIES[@]} -gt 0 ]; then
        PROXY="${PROXIES[RANDOM % ${#PROXIES[@]}]}"
        PROXY_OPT="--proxy $PROXY"
        print_info "   Proxy: ${PROXY%%@*}@***"
    fi
fi

print_info "[1/3] 📥 Baixando Reel"
cd "$WORK_DIR"
if ! yt-dlp $COOKIES_OPT $PROXY_OPT \
    --no-playlist \
    -f 'best[ext=mp4]/best' \
    -o 'video.%(ext)s' \
    "$REEL_URL"; then
    print_error "Não foi possível baixar o Reel"
    echo "O Instagram costuma exigir uma sessão logada."
    echo "Deixe o Chrome logado no Instagram ou coloque um cookies.txt na raiz do projeto."
    exit 1
fi

VIDEO_FILE=$(find . -maxdepth 1 -name 'video.*' -type f | head -1)
if [ -z "$VIDEO_FILE" ]; then
    print_error "Vídeo não foi baixado"
    exit 1
fi
VIDEO_FILE=$(basename "$VIDEO_FILE")
print_success "✅ Vídeo baixado: $VIDEO_FILE"
echo ""

if ! ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 "$VIDEO_FILE" | grep -q audio; then
    print_error "O arquivo baixado não tem faixa de áudio para transcrever"
    exit 1
fi

print_info "[2/3] 🎵 Extraindo áudio"
ffmpeg -y -i "$VIDEO_FILE" -vn -acodec libmp3lame -q:a 2 audio.mp3
print_success "✅ Áudio extraído"
echo ""

AUDIO_FILE="audio.mp3"
AUDIO_BYTES=$(wc -c < "$AUDIO_FILE" | tr -d ' ')
if [ "$AUDIO_BYTES" -gt "$WHISPER_MAX_BYTES" ]; then
    print_warning "Áudio acima de 25 MB. Recomprimindo para caber na Whisper API..."
    ffmpeg -y -i "$AUDIO_FILE" -ac 1 -ar 16000 -b:a 64k audio_compact.mp3
    AUDIO_FILE="audio_compact.mp3"
fi

print_info "[3/3] 🗣️  Transcrevendo áudio com Whisper API"
if ! curl -s -f https://api.openai.com/v1/audio/transcriptions \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -F "file=@${AUDIO_FILE}" \
    -F "model=whisper-1" \
    -F "response_format=verbose_json" \
    -o transcript.json; then
    print_error "Falha na transcrição"
    exit 1
fi

if [ ! -s transcript.json ]; then
    print_error "Transcrição vazia"
    exit 1
fi

ROTEIRO=$(jq -r '.text // empty' transcript.json)
if [ -z "$ROTEIRO" ]; then
    print_error "A resposta da API não trouxe texto transcrito"
    exit 1
fi

printf '%s\n' "$ROTEIRO" > roteiro.txt

print_header "Roteiro"
printf '%s\n' "$ROTEIRO"
echo ""
print_success "✅ Transcrição salva"
echo "  - $WORK_DIR/roteiro.txt"
echo "  - $WORK_DIR/transcript.json"
