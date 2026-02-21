#!/bin/bash
#
# Script para baixar vídeo do YouTube (standalone)
#
# Pode ser executado isoladamente ou como parte do fluxo do process_video.sh
#
# Uso:
#   ./download_video.sh <youtube_url> [output_dir]
#
# Se output_dir não for informado, cria um diretório com timestamp no diretório do script.

set -euo pipefail

# Cores para output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "$0")"

print_error() { echo -e "${RED}Erro: $1${NC}" >&2; }
print_success() { echo -e "${GREEN}$1${NC}"; }
print_info() { echo -e "${BLUE}$1${NC}"; }

# Verificar argumentos
if [ $# -lt 1 ]; then
    print_error "URL do YouTube não fornecida"
    echo "Uso: $SCRIPT_NAME <youtube_url> [output_dir]"
    exit 1
fi

readonly YOUTUBE_URL="$1"
readonly OUTPUT_DIR="${2:-${SCRIPT_DIR}/video_processing_$(date +%Y%m%d_%H%M%S)}"

# Verificar yt-dlp
if ! command -v yt-dlp &> /dev/null; then
    print_error "yt-dlp não encontrado. Instale com: brew install yt-dlp"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Cookies: evita erro "Sign in to confirm you're not a bot"
# Opção 1: arquivo cookies.txt no diretório do script
# Opção 2 (padrão): cookies do navegador. YT_DLP_COOKIES_BROWSER=safari|chrome|firefox
COOKIES_OPT=""
if [ -f "${SCRIPT_DIR}/cookies.txt" ]; then
    COOKIES_OPT="--cookies ${SCRIPT_DIR}/cookies.txt"
    print_info "   Cookies: cookies.txt"
else
    BROWSER="${YT_DLP_COOKIES_BROWSER:-chrome}"
    COOKIES_OPT="--cookies-from-browser $BROWSER"
    print_info "   Cookies: navegador $BROWSER"
fi

# Proxy rotativo: lê proxies.txt se existir (linhas com # são ignoradas)
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

print_info "📥 Baixando vídeo do YouTube"
print_info "   URL: $YOUTUBE_URL"
print_info "   Destino: $OUTPUT_DIR"
echo ""

yt-dlp $COOKIES_OPT $PROXY_OPT -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' -o 'video.%(ext)s' "$YOUTUBE_URL"

VIDEO_FILE=$(find . -maxdepth 1 -name 'video.*' -type f | head -1)
if [ -z "$VIDEO_FILE" ]; then
    print_error "Vídeo não foi baixado"
    exit 1
fi

VIDEO_FILE=$(basename "$VIDEO_FILE")
print_success "✅ Vídeo baixado: $VIDEO_FILE"
echo ""
echo "Arquivo: $OUTPUT_DIR/$VIDEO_FILE"
