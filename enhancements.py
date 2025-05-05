import re
import requests
from PIL import Image
import pytesseract
from io import BytesIO
import tweepy
from bs4 import BeautifulSoup
import openai

def validate_document_ocr(img_bytes, expected_name, expected_birth):
    """
    Extrai texto do documento e valida nome e data de nascimento.
    :param img_bytes: bytes da imagem enviada
    :param expected_name: nome informado pelo usuário
    :param expected_birth: data de nascimento DD/MM/AAAA
    :return: True se os dados conferirem
    """
    # Carrega imagem e converte para tons de cinza
    img = Image.open(BytesIO(img_bytes)).convert("L")
    # OCR
    text = pytesseract.image_to_string(img, lang='por')
    # Normaliza para maiúsculas sem acentos
    def normalize(s):
        s = s.upper()
        s = re.sub(r"[ÃÁÀÂÄ]", "A", s)
        s = re.sub(r"[ÉÈÊË]", "E", s)
        s = re.sub(r"[ÍÌÎÏ]", "I", s)
        s = re.sub(r"[ÓÒÔÖÕ]", "O", s)
        s = re.sub(r"[ÚÙÛÜ]", "U", s)
        return s
    text_norm = normalize(text)
    name_norm = normalize(expected_name)
    birth_norm = expected_birth.replace("/", "").strip()

    # Verifica presença de nome e ano de nascimento
    has_name = name_norm in text_norm
    # Buscamos a data no formato DDMMYYYY
    birth_match = re.search(r"\b" + re.escape(birth_norm) + r"\b", re.sub(r"/", "", text))
    return has_name and bool(birth_match)


def fetch_user_furia_interactions(twitter_api_key, twitter_api_secret, twitter_token, twitter_token_secret, username, max_tweets=50):
    """
    Autentica no Twitter e retorna tweets do usuário que mencionam 'FURIA' ou interações com @FURIA.
    :return: lista de objetos Status do Tweepy
    """
    auth = tweepy.OAuth1UserHandler(
        twitter_api_key, twitter_api_secret,
        twitter_token, twitter_token_secret
    )
    api = tweepy.API(auth, wait_on_rate_limit=True)
    tweets = api.user_timeline(screen_name=username, count=max_tweets, tweet_mode='extended')
    # Filtra menções
    furia_tweets = [t for t in tweets if 'FURIA' in t.full_text.upper() or '@FURIA' in t.full_text.upper()]
    return furia_tweets


def validate_esports_link(openai_api_key, url, user_profile_summary):
    """
    Scrape do link de e-sports e valida com GPT-4 se o conteúdo é relevante ao perfil.
    :param openai_api_key: chave da OpenAI
    :param url: link de Liquipedia, HLTV ou gosu.gg
    :param user_profile_summary: resumo de dados básicos do usuário
    :return: True se GPT-4 considerar relevante
    """
    # Pega conteúdo da página
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    # Extrai primeiro parágrafo ou título
    title = soup.find(['h1', 'h2', 'title'])
    content = title.get_text(strip=True) if title else ''

    openai.api_key = openai_api_key
    prompt = (
        f"Você é um modelo que verifica se um link de e-sports é relevante ao perfil do fã."
        f"O perfil do usuário: {user_profile_summary}."
        f"Conteúdo extraído: {content}."
        f"Responda apenas 'SIM' ou 'NÃO' se for relevante."
    )
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    answer = completion.choices[0].message.content.strip().upper()
    return answer.startswith('SIM')

# Exemplos de uso:
# 1) validate_document_ocr(uploaded.read(), st.session_state.name, st.session_state.birthdate)
# 2) fetch_user_furia_interactions(os.getenv('TW_API_KEY'), ... , st.session_state.twitter_handle)
# 3) validate_esports_link(os.getenv('OPENAI_KEY'), st.session_state.esports_link, resumo_do_perfil)
