#!/usr/bin/env python3
"""
Script para gerar arquivo SRT a partir da transcrição JSON do Whisper API.

Este módulo converte o formato JSON retornado pela API Whisper da OpenAI
para o formato SRT (SubRip), usado para legendas de vídeo.

Uso:
    python3 generate_srt.py transcript.json output.srt
"""

import json
import logging
import math
import sys
from typing import Any, Dict, List

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constantes
SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60
MILLISECONDS_PER_SECOND = 1000


def format_time(seconds: float) -> str:
    """
    Converte segundos para formato SRT: HH:MM:SS,mmm.
    
    Args:
        seconds: Tempo em segundos (pode ser float).
        
    Returns:
        String formatada no padrão SRT (HH:MM:SS,mmm).
    """
    hours = math.floor(seconds / SECONDS_PER_HOUR)
    minutes = math.floor((seconds % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE)
    secs = math.floor(seconds % SECONDS_PER_MINUTE)
    milliseconds = math.floor((seconds - math.floor(seconds)) * MILLISECONDS_PER_SECOND)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def load_transcript(transcript_file: str) -> Dict[str, Any]:
    """
    Carrega o arquivo JSON de transcrição.
    
    Args:
        transcript_file: Caminho para o arquivo JSON.
        
    Returns:
        Dicionário com os dados da transcrição.
        
    Raises:
        FileNotFoundError: Se o arquivo não existir.
        json.JSONDecodeError: Se o arquivo não for um JSON válido.
    """
    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Arquivo de transcrição não encontrado: {transcript_file}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {e}")
        raise


def generate_srt_content(segments: List[Dict[str, Any]]) -> str:
    """
    Gera conteúdo SRT a partir dos segmentos da transcrição.
    
    Args:
        segments: Lista de segmentos com 'start', 'end' e 'text'.
        
    Returns:
        String com conteúdo SRT formatado.
    """
    srt_lines: List[str] = []
    
    for index, segment in enumerate(segments, start=1):
        start_time = format_time(segment.get('start', 0))
        end_time = format_time(segment.get('end', 0))
        text = segment.get('text', '').strip()
        
        if not text:
            logger.warning(f"Segmento {index} sem texto, pulando...")
            continue
        
        srt_lines.append(str(index))
        srt_lines.append(f"{start_time} --> {end_time}")
        srt_lines.append(text)
        srt_lines.append("")  # Linha em branco entre segmentos
    
    return "\n".join(srt_lines)


def generate_srt(transcript_file: str, output_file: str) -> None:
    """
    Gera arquivo SRT a partir do JSON da transcrição.
    
    Args:
        transcript_file: Caminho para o arquivo JSON de transcrição.
        output_file: Caminho para o arquivo SRT de saída.
        
    Raises:
        SystemExit: Se houver erro crítico no processamento.
    """
    # Carregar transcrição
    try:
        data = load_transcript(transcript_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Erro ao carregar transcrição: {e}")
        sys.exit(1)
    
    # Extrair segmentos
    segments = data.get('segments', [])
    
    if not segments:
        logger.error("Nenhum segmento encontrado no arquivo JSON")
        sys.exit(1)
    
    logger.info(f"Processando {len(segments)} segmentos")
    
    # Gerar conteúdo SRT
    srt_content = generate_srt_content(segments)
    
    # Salvar arquivo SRT
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        logger.info(f"Arquivo SRT gerado com sucesso: {output_file}")
        logger.info(f"Total de segmentos: {len(segments)}")
        
    except IOError as e:
        logger.error(f"Erro ao salvar arquivo SRT: {e}")
        sys.exit(1)


def main() -> None:
    """Função principal do script."""
    if len(sys.argv) != 3:
        print("Uso: python3 generate_srt.py <transcript.json> <output.srt>")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    output_file = sys.argv[2]
    
    generate_srt(transcript_file, output_file)


if __name__ == '__main__':
    main()
