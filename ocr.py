import os
import re
import base64
import json
import logging

logger = logging.getLogger(__name__)

CATEGORIES = {
    'Alimentação': ['restaurante','almoço','jantar','lanche','café','cafe','ifood','rappi',
                    'burger','pizza','sushi','padaria','lanchonete','mcdonalds','subway'],
    'Transporte':  ['uber','taxi','99','posto','gasolina','combustivel','combustível',
                    'estacionamento','ônibus','metro','metrô','embarque'],
    'Saúde':       ['farmácia','farmacia','remédio','remedio','consulta','exame',
                    'academia','suplemento','drogaria','droga'],
    'Casa':        ['mercado','supermercado','condominio','condomínio','aluguel',
                    'energia','água','agua','internet','tim','claro','vivo'],
    'Lazer':       ['cinema','bar','show','jogo','netflix','spotify','amazon','steam'],
}

def _guess_category(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORIES.items():
        if any(kw in t for kw in kws):
            return cat
    return 'Outros'

def _to_float(s: str) -> float | None:
    """Convert '35', '35.90', '35,90' → float."""
    try:
        return float(s.replace(',', '.'))
    except ValueError:
        return None

def _parse_text(text: str):
    """Extract (amount, category, description) from typed string.

    Accepts any of:
      45.90 Almoço | 45,90 Almoço | 45 Almoço
      Uber 35.90   | Uber 35,90   | Uber 35
      R$ 45,90 Almoço
      45.90 (just a number)
      Qualquer coisa 0 (sem valor reconhecível → None)
    """
    text = text.strip()
    # Remove "R$" prefix
    text = re.sub(r'[Rr]\$\s*', '', text).strip()

    NUMBER = r'([\d]+(?:[.,][\d]{1,2})?)'

    # number first: "45.90 Almoço" or "45 Almoço"
    m = re.match(r'^' + NUMBER + r'\s+(.+)$', text)
    if m:
        v = _to_float(m.group(1))
        if v:
            desc = m.group(2).strip()
            return v, _guess_category(desc), desc

    # text first: "Uber 35.90" or "Uber 35"
    m = re.match(r'^(.+?)\s+' + NUMBER + r'$', text)
    if m:
        v = _to_float(m.group(2))
        if v:
            desc = m.group(1).strip()
            return v, _guess_category(desc), desc

    # just a number: "35" or "35.90"
    m = re.match(r'^' + NUMBER + r'$', text)
    if m:
        v = _to_float(m.group(1))
        if v:
            return v, 'Outros', 'Gasto'

    return None

def _parse_image(image_bytes: bytes):
    """Use Claude Haiku to extract expense from a receipt image."""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        b64 = base64.standard_b64encode(image_bytes).decode()
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=150,
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b64}},
                    {'type': 'text',  'text':
                        'Extrai o valor total e o estabelecimento deste comprovante. '
                        'Responda APENAS em JSON: {"amount": 45.90, "description": "Restaurante X"}. '
                        'Se não conseguir, responda: {"amount": null}'}
                ]
            }]
        )
        text = resp.content[0].text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if data.get('amount'):
                desc = data.get('description', 'Gasto')
                return float(data['amount']), _guess_category(desc), desc
    except Exception as e:
        logger.error("Claude OCR error: %s", e)
    return None

def extract_expense(data: bytes, is_image: bool = False):
    """Returns (amount, category, description) or None."""
    if is_image:
        return _parse_image(data)
    return _parse_text(data.decode('utf-8', errors='ignore'))
