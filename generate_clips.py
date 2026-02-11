#!/usr/bin/env python3
"""
Script para gerar clips do vídeo baseado nos highlights encontrados.

Este módulo processa um arquivo JSON com highlights e gera clips de vídeo
usando ffmpeg para cada segmento identificado.

Uso:
    python3 generate_clips.py <video.mp4> <highlights.json> <output_dir>
"""

import json
import logging
import math
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constantes
FFPROBE_CMD = 'ffprobe'
FFMPEG_CMD = 'ffmpeg'
CLIP_FILENAME_FORMAT = "clip_{index:02d}_{start}s_{end}s.mp4"
REASON_PREVIEW_LENGTH = 80


class VideoProcessingError(Exception):
    """Exceção customizada para erros no processamento de vídeo."""
    pass


def get_video_duration(video_path: str) -> int:
    """
    Obtém a duração do vídeo usando ffprobe.
    
    Args:
        video_path: Caminho para o arquivo de vídeo.
        
    Returns:
        Duração do vídeo em segundos (arredondada para baixo).
        
    Raises:
        VideoProcessingError: Se houver erro ao executar ffprobe.
        FileNotFoundError: Se ffprobe não estiver instalado.
    """
    try:
        result = subprocess.run(
            [
                FFPROBE_CMD,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        duration = float(result.stdout.strip())
        return math.floor(duration)
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Erro ao obter duração do vídeo: {e.stderr}"
        logger.error(error_msg)
        raise VideoProcessingError(error_msg) from e
        
    except FileNotFoundError:
        error_msg = "ffprobe não encontrado. Certifique-se de que ffmpeg está instalado."
        logger.error(error_msg)
        raise


def cut_clip(video_path: str, start: float, end: float, output_path: str) -> bool:
    """
    Corta um clip do vídeo usando ffmpeg.
    
    Args:
        video_path: Caminho para o vídeo original.
        start: Tempo de início em segundos.
        end: Tempo de fim em segundos.
        output_path: Caminho para salvar o clip.
        
    Returns:
        True se o clip foi gerado com sucesso, False caso contrário.
        
    Raises:
        FileNotFoundError: Se ffmpeg não estiver instalado.
    """
    duration = end - start
    
    try:
        subprocess.run(
            [
                FFMPEG_CMD,
                '-y',
                '-ss', str(start),
                '-i', video_path,
                '-t', str(duration),
                '-c:v', 'copy',
                '-c:a', 'copy',
                output_path
            ],
            check=True,
            capture_output=True
        )
        return True
        
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.decode('utf-8', errors='ignore')
        logger.error(f"Erro ao cortar clip de {start}s a {end}s: {error_output}")
        return False
        
    except FileNotFoundError:
        error_msg = "ffmpeg não encontrado. Certifique-se de que ffmpeg está instalado."
        logger.error(error_msg)
        raise

def load_highlights(highlights_file: str) -> List[Dict[str, Any]]:
    """
    Carrega highlights do arquivo JSON.
    
    Args:
        highlights_file: Caminho para o arquivo JSON de highlights.
        
    Returns:
        Lista de highlights.
        
    Raises:
        FileNotFoundError: Se o arquivo não existir.
        json.JSONDecodeError: Se o arquivo não for JSON válido.
    """
    try:
        with open(highlights_file, 'r', encoding='utf-8') as f:
            highlights = json.load(f)
        
        if not isinstance(highlights, list):
            raise ValueError("Arquivo de highlights deve conter uma lista")
        
        return highlights
        
    except FileNotFoundError:
        logger.error(f"Arquivo de highlights não encontrado: {highlights_file}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {e}")
        raise


def validate_clip_timing(start: float, end: float, video_duration: int) -> Optional[tuple]:
    """
    Valida e ajusta os tempos do clip para não ultrapassar a duração do vídeo.
    
    Args:
        start: Tempo de início em segundos.
        end: Tempo de fim em segundos.
        video_duration: Duração total do vídeo em segundos.
        
    Returns:
        Tupla (start, end) ajustada, ou None se inválido.
    """
    if start >= video_duration:
        return None
    
    if end > video_duration:
        end = float(video_duration)
    
    if start >= end:
        return None
    
    return (start, end)


def generate_clip_filename(index: int, start: float, end: float) -> str:
    """
    Gera nome do arquivo para o clip.
    
    Args:
        index: Índice do clip (1-based).
        start: Tempo de início em segundos.
        end: Tempo de fim em segundos.
        
    Returns:
        Nome do arquivo formatado.
    """
    return CLIP_FILENAME_FORMAT.format(
        index=index,
        start=int(start),
        end=int(end)
    )


def generate_clips(video_path: str, highlights_file: str, output_dir: str) -> None:
    """
    Gera clips baseado nos highlights encontrados.
    
    Args:
        video_path: Caminho para o arquivo de vídeo.
        highlights_file: Caminho para o arquivo JSON de highlights.
        output_dir: Diretório para salvar os clips.
        
    Raises:
        SystemExit: Se houver erro crítico no processamento.
    """
    # Verificar se o vídeo existe
    if not os.path.exists(video_path):
        logger.error(f"Vídeo não encontrado: {video_path}")
        sys.exit(1)
    
    # Carregar highlights
    try:
        highlights = load_highlights(highlights_file)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Erro ao carregar highlights: {e}")
        sys.exit(1)
    
    if not highlights:
        logger.error("Nenhum highlight encontrado no arquivo")
        sys.exit(1)
    
    # Criar diretório de saída
    os.makedirs(output_dir, exist_ok=True)
    
    # Obter duração do vídeo
    try:
        video_duration = get_video_duration(video_path)
    except (VideoProcessingError, FileNotFoundError) as e:
        logger.error(f"Erro ao obter duração do vídeo: {e}")
        sys.exit(1)
    
    logger.info(f"Duração do vídeo: {video_duration}s")
    logger.info(f"Gerando {len(highlights)} clips...\n")
    
    # Gerar cada clip
    successful = 0
    failed = 0
    
    for i, highlight in enumerate(highlights, 1):
        start = float(highlight.get('start', 0))
        end = float(highlight.get('end', start + 30))
        reason = highlight.get('reason', '')
        
        # Validar e ajustar timing
        timing = validate_clip_timing(start, end, video_duration)
        if timing is None:
            logger.warning(
                f"Clip {i}: Timing inválido (start={start}s, end={end}s, "
                f"duration={video_duration}s). Pulando..."
            )
            failed += 1
            continue
        
        start, end = timing
        
        # Gerar nome do arquivo
        output_filename = generate_clip_filename(i, start, end)
        output_path = os.path.join(output_dir, output_filename)
        
        logger.info(
            f"Clip {i}/{len(highlights)}: {start:.1f}s - {end:.1f}s "
            f"({end-start:.1f}s)"
        )
        
        if reason:
            preview_reason = (
                reason[:REASON_PREVIEW_LENGTH] + '...'
                if len(reason) > REASON_PREVIEW_LENGTH
                else reason
            )
            logger.info(f"Motivo: {preview_reason}")
        
        # Gerar clip
        try:
            if cut_clip(video_path, start, end, output_path):
                logger.info(f"Salvo: {output_filename}\n")
                successful += 1
            else:
                logger.error(f"Falha ao gerar clip\n")
                failed += 1
                
        except FileNotFoundError:
            logger.error("ffmpeg não encontrado")
            sys.exit(1)
    
    # Resumo final
    print(f"\n{'='*50}")
    print(f"✅ Clips gerados com sucesso: {successful}")
    if failed > 0:
        print(f"❌ Clips com falha: {failed}")
    print(f"📁 Pasta de saída: {output_dir}")


def main() -> None:
    """Função principal do script."""
    if len(sys.argv) != 4:
        print("Uso: python3 generate_clips.py <video.mp4> <highlights.json> <output_dir>")
        print("\nExemplo:")
        print("  python3 generate_clips.py video.mp4 highlights.json ./clips")
        sys.exit(1)
    
    video_path = sys.argv[1]
    highlights_file = sys.argv[2]
    output_dir = sys.argv[3]
    
    generate_clips(video_path, highlights_file, output_dir)


if __name__ == '__main__':
    main()
