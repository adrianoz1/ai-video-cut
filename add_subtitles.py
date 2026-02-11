#!/usr/bin/env python3
"""
Script para adicionar legendas ao vídeo e converter para vertical (9:16).

Este módulo adiciona legendas a um vídeo usando diferentes métodos (ASS, drawtext,
ou soft subtitles) e converte o vídeo para formato vertical (9:16) adequado para
TikTok, Reels e YouTube Shorts.

Uso:
    python3 add_subtitles.py <video.mp4> <subtitles.srt> <output.mp4>
"""

import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import List, Optional, Tuple

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constantes
FFMPEG_CMD = 'ffmpeg'
ASS_RESOLUTION_X = 1920
ASS_RESOLUTION_Y = 1080
FONT_SIZE = 52
BORDER_WIDTH = 3
BOTTOM_MARGIN = 100
VERTICAL_WIDTH = 1080
VERTICAL_HEIGHT = 1920
VIDEO_TIMEOUT = 1200  # 20 minutos
ASS_STYLE_LINE = (
    "Style: Active,Arial,52,&H0000FFFF,&H0000FFFF,&H00000000,"
    "&H64000000,1,0,0,0,100,100,0,0,1,3,0,2,80,80,100,1"
)

SRT_TIME_PATTERN = re.compile(
    r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})'
)
SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60
MILLISECONDS_PER_SECOND = 1000


class SubtitleProcessingError(Exception):
    """Exceção customizada para erros no processamento de legendas."""
    pass


def parse_srt(srt_path: str) -> List[Tuple[float, float, str]]:
    """
    Parse arquivo SRT e retorna lista de segmentos.
    
    Args:
        srt_path: Caminho para o arquivo SRT.
        
    Returns:
        Lista de tuplas (start, end, text) onde start e end estão em segundos.
        
    Raises:
        FileNotFoundError: Se o arquivo não existir.
    """
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logger.error(f"Arquivo SRT não encontrado: {srt_path}")
        raise
    
    blocks = re.split(r'\n\s*\n', content.strip())
    segments: List[Tuple[float, float, str]] = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        
        # Linha 1: tempo (00:00:00,000 --> 00:00:07,519)
        time_line = lines[1]
        match = SRT_TIME_PATTERN.match(time_line)
        if not match:
            continue
        
        # Converter tempo para segundos
        start = (
            int(match.group(1)) * SECONDS_PER_HOUR +
            int(match.group(2)) * SECONDS_PER_MINUTE +
            int(match.group(3)) +
            int(match.group(4)) / MILLISECONDS_PER_SECOND
        )
        end = (
            int(match.group(5)) * SECONDS_PER_HOUR +
            int(match.group(6)) * SECONDS_PER_MINUTE +
            int(match.group(7)) +
            int(match.group(8)) / MILLISECONDS_PER_SECOND
        )
        
        text = ' '.join(lines[2:]).strip()
        text = re.sub(r'\s+', ' ', text)
        
        if text:
            segments.append((start, end, text))
    
    return segments

def _format_ass_time(seconds: float) -> str:
    """
    Formata tempo em segundos para formato ASS (H:MM:SS.CC).
    
    Args:
        seconds: Tempo em segundos.
        
    Returns:
        String formatada no padrão ASS.
    """
    h = int(seconds // SECONDS_PER_HOUR)
    m = int((seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE)
    s = int(seconds % SECONDS_PER_MINUTE)
    centiseconds = int(round((seconds - int(seconds)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{min(99, centiseconds):02d}"


def build_ass_content(segments: List[Tuple[float, float, str]]) -> str:
    """
    Gera conteúdo ASS estilo TikTok (palavras aparecendo uma a uma, amarelo).
    
    Args:
        segments: Lista de segmentos (start, end, text).
        
    Returns:
        String com conteúdo ASS formatado.
    """
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {ASS_RESOLUTION_X}
PlayResY: {ASS_RESOLUTION_Y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{ASS_STYLE_LINE}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    lines = [header]
    
    for start, end, text in segments:
        text = text.replace('\r', '').replace('\n', '\\N')
        if not text:
            continue
        
        duration = end - start
        words = re.split(r'\s+', text)
        num_words = len(words)
        
        if num_words > 0 and duration > 0:
            word_duration = duration / num_words
            for i in range(num_words):
                word_start = start + i * word_duration
                word_end = start + (i + 1) * word_duration
                word = words[i]
                lines.append(
                    f"Dialogue: 0,{_format_ass_time(word_start)},"
                    f"{_format_ass_time(word_end)},Active,,0,0,0,,{word}"
                )
    
    return '\n'.join(lines)

def try_ass_style(video_path: str, srt_path: str, output_path: str) -> bool:
    """
    Tenta adicionar legendas usando ASS (estilo TikTok).
    
    Args:
        video_path: Caminho para o vídeo original.
        srt_path: Caminho para o arquivo SRT.
        output_path: Caminho para salvar o vídeo com legendas.
        
    Returns:
        True se bem-sucedido, False caso contrário.
    """
    logger.info("Tentando método ASS (legendas queimadas estilo TikTok)...")
    
    try:
        segments = parse_srt(srt_path)
    except FileNotFoundError:
        return False
    
    if not segments:
        logger.warning("Nenhum segmento encontrado no SRT")
        return False
    
    # Criar arquivo ASS temporário
    ass_content = build_ass_content(segments)
    ass_path: Optional[str] = None
    
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.ass', delete=False, encoding='utf-8'
        ) as f:
            ass_path = f.name
            f.write(ass_content)
        
        # Escapar caminho para FFmpeg (especialmente no macOS)
        abs_ass_path = os.path.abspath(ass_path)
        escaped_path = abs_ass_path.replace(':', '\\:')
        
        cmd = [
            FFMPEG_CMD, '-y',
            '-i', video_path,
            '-vf', f"subtitles=filename='{escaped_path}'",
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-threads', '2',
            '-movflags', '+faststart',
            output_path
        ]
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=VIDEO_TIMEOUT
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info("Legendas ASS aplicadas com sucesso!")
            return True
        
        # Verificar se é erro de filtro não encontrado
        if 'No such filter' in result.stderr or 'Filter not found' in result.stderr:
            logger.warning("Filtro ASS não disponível")
            return False
        
        logger.warning(f"Erro ao aplicar ASS: {result.stderr[:200]}")
        return False
    
    finally:
        if ass_path and os.path.exists(ass_path):
            os.unlink(ass_path)

def try_tiktok_drawtext(video_path: str, srt_path: str, output_path: str) -> bool:
    """
    Tenta adicionar legendas usando drawtext (fallback).
    
    Args:
        video_path: Caminho para o vídeo original.
        srt_path: Caminho para o arquivo SRT.
        output_path: Caminho para salvar o vídeo com legendas.
        
    Returns:
        True se bem-sucedido, False caso contrário.
    """
    logger.info("Tentando método drawtext (TikTok style)...")
    
    try:
        segments = parse_srt(srt_path)
    except FileNotFoundError:
        return False
    
    if not segments:
        return False
    
    # Construir filtro drawtext
    parts: List[str] = []
    for start, end, text in segments:
        # Escapar caracteres especiais para drawtext
        escaped = (
            text.replace('\\', '\\\\')
                .replace("'", "\\'")
                .replace('%', '%%')
        )
        parts.append(
            f"drawtext=enable='between(t,{start},{end})':text='{escaped}':"
            f"fontsize={FONT_SIZE}:fontcolor=white:bordercolor=black:"
            f"borderw={BORDER_WIDTH}:x=(w-text_w)/2:y=h-th-{BOTTOM_MARGIN}"
        )
    
    filter_str = ','.join(parts)
    
    try:
        cmd = [
            FFMPEG_CMD, '-y',
            '-i', video_path,
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'copy',
            output_path
        ]
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=VIDEO_TIMEOUT
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info("Legendas drawtext aplicadas com sucesso!")
            return True
        
        if 'No such filter' in result.stderr or 'Filter not found' in result.stderr:
            logger.warning("Filtro drawtext não disponível")
            return False
        
        logger.warning(f"Erro ao aplicar drawtext: {result.stderr[:200]}")
        return False
    
    except subprocess.TimeoutExpired:
        logger.warning("Timeout ao aplicar drawtext")
        return False

def mux_soft_subtitles(video_path: str, srt_path: str, output_path: str) -> bool:
    """
    Adiciona legendas como stream (soft subtitles) - funciona sempre.
    
    Args:
        video_path: Caminho para o vídeo original.
        srt_path: Caminho para o arquivo SRT.
        output_path: Caminho para salvar o vídeo com legendas.
        
    Returns:
        True se bem-sucedido, False caso contrário.
    """
    logger.info("Usando método soft subtitles (legendas em stream)...")
    
    cmd = [
        FFMPEG_CMD, '-y',
        '-i', video_path,
        '-i', srt_path,
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-c:s', 'mov_text',
        '-metadata:s:s:0', 'language=por',
        '-disposition:s:0', 'default',
        '-map', '0:v',
        '-map', '0:a',
        '-map', '1:s',
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=VIDEO_TIMEOUT
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info("Legendas soft subtitles aplicadas!")
            return True
        
        logger.error(f"Erro ao aplicar soft subtitles: {result.stderr[:200]}")
        return False
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout ao aplicar soft subtitles")
        return False

def convert_to_vertical(video_path: str, output_path: str) -> bool:
    """
    Converte vídeo para vertical 9:16 (1080x1920).
    
    Args:
        video_path: Caminho para o vídeo original.
        output_path: Caminho para salvar o vídeo vertical.
        
    Returns:
        True se bem-sucedido, False caso contrário.
    """
    logger.info("Convertendo para vertical (9:16)...")
    
    temp_path = output_path + '.vertical.mp4'
    
    # Crop centro para 9:16, depois scale para 1080x1920
    filter_str = (
        f"crop='min(iw,ih*9/16)':ih:'(iw-min(iw,ih*9/16))/2':0,"
        f"scale={VERTICAL_WIDTH}:{VERTICAL_HEIGHT}"
    )
    
    cmd = [
        FFMPEG_CMD, '-y',
        '-i', video_path,
        '-vf', filter_str,
        '-c:a', 'copy',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        temp_path
    ]
    
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=VIDEO_TIMEOUT
        )
        
        if result.returncode == 0 and os.path.exists(temp_path):
            # Substituir arquivo original
            if os.path.exists(output_path):
                os.unlink(output_path)
            os.rename(temp_path, output_path)
            logger.info("Conversão para vertical concluída!")
            return True
        
        logger.error(f"Erro na conversão vertical: {result.stderr[:200]}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False
    
    except subprocess.TimeoutExpired:
        logger.error("Timeout na conversão vertical")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False

def add_subtitles(video_path: str, srt_path: str, output_path: str) -> None:
    """
    Adiciona legendas ao vídeo e converte para vertical.
    
    Args:
        video_path: Caminho para o vídeo original.
        srt_path: Caminho para o arquivo SRT.
        output_path: Caminho para salvar o vídeo final.
        
    Raises:
        SystemExit: Se houver erro crítico no processamento.
    """
    # Validar arquivos de entrada
    if not os.path.exists(video_path):
        logger.error(f"Vídeo não encontrado: {video_path}")
        sys.exit(1)
    
    if not os.path.exists(srt_path):
        logger.error(f"Arquivo SRT não encontrado: {srt_path}")
        sys.exit(1)
    
    # Criar diretório de saída se necessário
    output_dir = os.path.dirname(output_path) if os.path.dirname(output_path) else '.'
    os.makedirs(output_dir, exist_ok=True)
    
    # Remover arquivo de saída se já existir
    if os.path.exists(output_path):
        logger.warning(f"Removendo arquivo existente: {output_path}")
        os.unlink(output_path)
    
    # Tentar métodos em ordem de preferência
    temp_output = output_path + '.with_subs.mp4'
    success = False
    
    success = try_ass_style(video_path, srt_path, temp_output)
    if not success:
        success = try_tiktok_drawtext(video_path, srt_path, temp_output)
    if not success:
        success = mux_soft_subtitles(video_path, srt_path, temp_output)
    
    if not success:
        logger.error("Falha ao adicionar legendas")
        sys.exit(1)
    
    # Converter para vertical
    if not convert_to_vertical(temp_output, output_path):
        logger.error("Falha na conversão vertical")
        sys.exit(1)
    
    # Limpar arquivo temporário
    if os.path.exists(temp_output):
        os.unlink(temp_output)
    
    logger.info(f"Vídeo final gerado: {output_path}")


def main() -> None:
    """Função principal do script."""
    if len(sys.argv) != 4:
        print("Uso: python3 add_subtitles.py <video.mp4> <subtitles.srt> <output.mp4>")
        print("\nExemplo:")
        print("  python3 add_subtitles.py video.mp4 subtitles.srt video_with_subs.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    srt_path = sys.argv[2]
    output_path = sys.argv[3]
    
    add_subtitles(video_path, srt_path, output_path)


if __name__ == '__main__':
    main()
