#!/usr/bin/env python3
"""
Script para encontrar os melhores momentos (highlights) do vídeo usando GPT.

Este módulo analisa transcrições de vídeo e identifica segmentos com maior
potencial viral usando a API da OpenAI GPT-4o-mini.

Uso:
    python3 find_highlights.py transcript.json highlights.json [OPENAI_API_KEY]

Ou defina OPENAI_API_KEY como variável de ambiente.
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constantes
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TEMPERATURE = 0.4
PREVIEW_REASON_LENGTH = 60


def load_transcript(transcript_file: str) -> Dict[str, Any]:
    """
    Carrega o arquivo de transcrição JSON.
    
    Args:
        transcript_file: Caminho para o arquivo JSON de transcrição.
        
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


def build_text_from_segments(segments: List[Dict[str, Any]]) -> str:
    """
    Monta texto compacto com timestamps para análise pela IA.
    
    Args:
        segments: Lista de segmentos da transcrição.
        
    Returns:
        String formatada com timestamps e textos dos segmentos.
    """
    lines: List[str] = []
    for segment in segments:
        start = segment.get('start', 0)
        end = segment.get('end', 0)
        text = segment.get('text', '')
        lines.append(f"[{start} - {end}] {text}")
    return "\n".join(lines)

def _build_prompt(transcript_text: str) -> str:
    """
    Constrói o prompt para a API da OpenAI.
    
    Args:
        transcript_text: Texto formatado da transcrição.
        
    Returns:
        String com o prompt completo.
    """
    return f"""You are a specialist in editing viral short-form videos for TikTok, Reels, and YouTube Shorts.

Your task is to analyze the transcript provided by the user and identify the segments with the highest potential for retention, sharing, and comments. The selected segments must function as fully independent videos.

Selection criteria (mandatory):

Each segment must:
- Have a strong hook within the first 3–5 seconds (impactful statement, strong opinion, provocative question, or expectation break).
- Contain a complete idea with clear beginning, development, and explicit conclusion.
- Not depend on previous or external context.
- Include at least one of the following elements: strong emotion, controversy, surprise, revelation, bold opinion, impactful statement, or a short story with a clear takeaway.

Start and end rules (mandatory):

- The segment must begin at the start of a complete sentence.
- The segment must end only after the full conclusion of a thought.
- The last second must contain a complete declarative sentence.
- The segment must not end with unfinished connectors (e.g., because, but, so, therefore, however, and, etc.), incomplete ideas, promises of continuation, or sentences that depend on what comes next.

If a segment reaches 30 seconds but the idea is not fully concluded, expand the segment until the thought is fully completed, respecting the maximum limit of 120 seconds.

If it is not possible to fully conclude the idea before reaching 120 seconds, discard the segment.

Technical rules (mandatory):

- Return between 3 and 6 segments.
- Each segment must contain:
  - start (in seconds)
  - end (in seconds)
  - reason (objective explanation of the viral potential)
- Duration must be calculated as: duration = end - start.
- All segments must strictly satisfy: 30 ≤ (end - start) ≤ 120.
- Do not return any segment shorter than 30 seconds.
- Do not return any segment longer than 120 seconds.
- Timestamps must strictly respect the transcript boundaries.

Final validation before responding:

For each segment, internally confirm that:
- It works as a standalone video.
- The ending delivers a clear sense of closure.
- The viewer would not feel that something is missing.
- The hook appears immediately at the beginning.

Return ONLY valid JSON in the following format:

[
  {{
    "start": 12,
    "end": 68,
    "reason": "Strong opening hook and bold opinion followed by a complete narrative arc with a clear conclusion."
  }}
]

transcript: 
{transcript_text}"""


def _extract_json_from_response(content: str) -> str:
    """
    Extrai JSON da resposta da API, removendo markdown se presente.
    
    Args:
        content: Conteúdo bruto da resposta.
        
    Returns:
        String JSON limpa.
    """
    content = content.strip()
    # Remove markdown code blocks
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    return content.strip()


def _call_openai_api(api_key: str, prompt: str) -> str:
    """
    Chama a API da OpenAI para encontrar highlights.
    
    Args:
        api_key: Chave da API OpenAI.
        prompt: Prompt formatado para a API.
        
    Returns:
        Conteúdo da resposta da API.
        
    Raises:
        urllib.error.HTTPError: Se houver erro na requisição HTTP.
        ValueError: Se a resposta não contiver dados válidos.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": OPENAI_TEMPERATURE
    }
    
    json_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        OPENAI_API_URL,
        data=json_data,
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            result = json.loads(response_data)
            
            if 'choices' not in result or not result['choices']:
                raise ValueError("Resposta da API não contém 'choices'")
            
            content = result['choices'][0]['message']['content']
            return content
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Erro HTTP {e.code} na API OpenAI: {error_body}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar resposta da API: {e}")
        raise ValueError(f"Resposta inválida da API: {e}")


def _save_highlights(highlights: List[Dict[str, Any]], output_file: str) -> None:
    """
    Salva highlights em arquivo JSON e exibe preview.
    
    Args:
        highlights: Lista de highlights encontrados.
        output_file: Caminho do arquivo de saída.
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(highlights, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Highlights salvos em: {output_file}")
    logger.info(f"Total de highlights: {len(highlights)}")
    
    # Preview dos highlights
    print("\n📌 Preview dos highlights:")
    for i, highlight in enumerate(highlights, 1):
        start = highlight.get('start', 0)
        end = highlight.get('end', 0)
        reason = highlight.get('reason', '')
        duration = end - start
        preview_reason = reason[:PREVIEW_REASON_LENGTH] + '...' if len(reason) > PREVIEW_REASON_LENGTH else reason
        print(f"  {i}. {start:.1f}s - {end:.1f}s ({duration:.1f}s) - {preview_reason}")


def find_highlights(transcript_file: str, output_file: str, api_key: str) -> None:
    """
    Encontra highlights usando GPT-4o-mini.
    
    Args:
        transcript_file: Caminho para o arquivo JSON de transcrição.
        output_file: Caminho para salvar o arquivo JSON de highlights.
        api_key: Chave da API OpenAI.
        
    Raises:
        SystemExit: Se houver erro crítico no processamento.
    """
    # Carregar transcrição
    try:
        transcript = load_transcript(transcript_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Erro ao carregar transcrição: {e}")
        sys.exit(1)
    
    segments = transcript.get('segments', [])
    
    if not segments:
        logger.error("Nenhum segmento encontrado no arquivo JSON")
        sys.exit(1)
    
    logger.info(f"Carregados {len(segments)} segmentos da transcrição")
    
    # Montar texto compacto
    transcript_text = build_text_from_segments(segments)
    
    # Chamar API OpenAI
    logger.info("Analisando transcrição e buscando highlights...")
    
    try:
        prompt = _build_prompt(transcript_text)
        content = _call_openai_api(api_key, prompt)
    except (urllib.error.HTTPError, ValueError) as e:
        logger.error(f"Erro ao chamar API OpenAI: {e}")
        sys.exit(1)
    
    # Extrair JSON da resposta
    json_content = _extract_json_from_response(content)
    
    # Parsear e salvar highlights
    try:
        highlights = json.loads(json_content)
        
        if not isinstance(highlights, list):
            raise ValueError("Resposta não é uma lista de highlights")
        
        _save_highlights(highlights, output_file)
        
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao parsear JSON da resposta: {e}")
        logger.debug(f"Conteúdo recebido: {json_content[:500]}...")
        # Salvar resposta bruta para debug
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
        logger.info(f"Resposta bruta salva em: {output_file}")
        sys.exit(1)

def get_api_key() -> str:
    """
    Obtém a chave da API OpenAI dos argumentos ou variável de ambiente.
    
    Returns:
        Chave da API OpenAI.
        
    Raises:
        SystemExit: Se a chave não for encontrada.
    """
    if len(sys.argv) >= 4:
        return sys.argv[3]
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY não encontrada")
        print("Defina como argumento ou variável de ambiente")
        sys.exit(1)
    
    return api_key


def main() -> None:
    """Função principal do script."""
    if len(sys.argv) < 3:
        print("Uso: python3 find_highlights.py <transcript.json> <highlights.json> [OPENAI_API_KEY]")
        print("\nOu defina a variável de ambiente OPENAI_API_KEY")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    output_file = sys.argv[2]
    api_key = get_api_key()
    
    find_highlights(transcript_file, output_file, api_key)


if __name__ == '__main__':
    main()
