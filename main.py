import os
import streamlit as st
import sqlite3
from datetime import datetime
import time
from PIL import Image
import requests
import pandas as pd
from dotenv import load_dotenv
from types import SimpleNamespace
from enhancements import (
    validate_document_ocr,
    fetch_user_furia_interactions,
    validate_esports_link
)

# Carrega variáveis de ambiente, sobrescrevendo as existentes
load_dotenv(override=True)

# Configurações iniciais
st.set_page_config(
    page_title="Know Your FURIA Fan",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Banco de Dados
conn = sqlite3.connect('knowyourfan.db', check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS tweets_cache (
    tweet_id TEXT PRIMARY KEY,
    author_id TEXT,
    text TEXT,
    created_at TEXT,
    fetched_at INTEGER
)
""")

# Tenta importar Tweepy e snscrape
try:
    import tweepy
except ImportError:
    tweepy = None

try:
    import snscrape.modules.twitter as sntwitter
except ImportError:
    sntwitter = None

# Funções Auxiliares

def load_furia_logo():
    try:
        url = "https://cdn.furia.com.br/assets/furia-logo.png"
        return Image.open(requests.get(url, timeout=2, stream=True).raw)
    except:
        return None


def validate_document(img_bytes):
    # usa OCR e confere nome + data de nascimento
    return validate_document_ocr(
        img_bytes,
        st.session_state.name,
        st.session_state.birthdate
    )

# CSS customizado para tweets
st.markdown(
    """
    <style>
      /* permite ambos os esquemas */
      :root { color-scheme: light dark; }

      /* estilo comum (do “antigo”) */
      .tweet-card {
          border-radius: 12px;
          padding: 12px;
          margin-bottom: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          border: 1px solid transparent;   /* será sobrescrito por cada tema */
      }
      .tweet-header {
          display: flex;
          align-items: center;
          margin-bottom: 8px;
      }
      .tweet-avatar {
          border-radius: 50%;
          width: 40px;
          height: 40px;
          margin-right: 8px;
          border: 1px solid transparent;   /* será sobrescrito no dark */
      }
      .tweet-user {
          font-weight: bold;
          margin-right: 4px;
      }
      .tweet-handle {
          margin-right: 4px;
      }
      .tweet-time {
          font-size: 0.85em;
      }
      .tweet-text {
          white-space: pre-wrap;
          line-height: 1.4;
      }

      /* LIGHT — quando o usuário prefere claro */
      @media (prefers-color-scheme: light) {
        body, .sidebar .sidebar-content {
          background-color: #FFFFFF;
          color: #000000;
        }
        .tweet-card {
          background: #f8f9fa;
          border-color: #DDD;
        }
        .tweet-text { color: #111; }
        .tweet-header span { color: #555; }
      }

      /* DARK — quando o usuário prefere escuro */
      @media (prefers-color-scheme: dark) {
        body, .sidebar .sidebar-content {
          background-color: #0E1117;
          color: #E1E8EE;
        }
        .tweet-card {
          background: #26272f;      /* ajustado conforme sua sugestão */
          border-color: #38444D;
          box-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }
        .tweet-text { color: #D9DADB; }
        .tweet-header span { color: #8899A6; }
        .tweet-avatar { border-color: #38444D; }
      }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar: Modo e Logo
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
st.sidebar.title("* Modo")
mode = st.sidebar.radio("Escolha o modo:", ['Fã ❤', 'Admin 🔑'])
logo = load_furia_logo()
if logo:
    st.sidebar.image(logo, use_column_width=True)

# Configura cliente Tweepy
BEARER = os.getenv("TWITTER_BEARER_TOKEN")
client = tweepy.Client(bearer_token=BEARER) if BEARER and tweepy else None
# quanto tempo (em segundos) o cache é válido
CACHE_TTL = 10 * 60 

# Cache para tweets via API (com expansões de usuário)
@st.cache_data(ttl=60)
def fetch_latest_tweets(username: str, count: int = 5):
    # 1) olha cache
    cutoff = int(time.time()) - CACHE_TTL
    # pega tweets já buscados recentemente
    rows = c.execute(
        "SELECT tweet_id, author_id, text, created_at FROM tweets_cache "
        "WHERE fetched_at > ? "
        "ORDER BY created_at DESC LIMIT ?",
        (cutoff, count)
    ).fetchall()
    if len(rows) >= count:
        # converte rows em objetos “fake” com atributos .data e includes
        tweets = []
        users = {}
        for tid, aid, txt, c_at in rows:
            t = SimpleNamespace(
                id=tid,
                author_id=aid,
                text=txt,
                created_at=datetime.fromisoformat(c_at)
            )
            tweets.append(t)
        return tweets, users

    # 2) se cache insuficiente, chama API
    user_resp = client.get_user(username=username)
    uid = user_resp.data.id
    resp = client.get_users_tweets(
        id=uid,
        max_results=count,
        tweet_fields=["created_at", "text", "author_id"],
        expansions=["author_id"],
        user_fields=["username", "name", "profile_image_url"]
    )
    tweets = resp.data or []
    # 3) grava no cache
    now = int(time.time())
    for t in tweets:
        c.execute(
            "INSERT OR REPLACE INTO tweets_cache (tweet_id, author_id, text, created_at, fetched_at) "
            "VALUES (?,?,?,?,?)",
            (t.id, t.author_id, t.text, t.created_at.isoformat(), now)
        )
    conn.commit()
    users = {}
    if resp.includes and "users" in resp.includes:
        users = {u.id: u for u in resp.includes["users"]}
    return tweets, users

# Fallback snscrape

def fetch_latest_tweets_snscrape(username: str, count: int = 5):
    if not sntwitter:
        return []
    tweets = []
    for i, tweet in enumerate(sntwitter.TwitterUserScraper(username).get_items()):
        if i >= count:
            break
        tweets.append(tweet)
    return tweets

# --- Modo Fã ---
if mode.startswith('Fã'):
    st.sidebar.subheader("Últimos Tweets da FURIA")

    if client:
        try:
            tweets, users = fetch_latest_tweets("FURIA", count=5)
        except tweepy.TooManyRequests:
            st.sidebar.warning("🚧 Limite de requisições atingido. Fallback via snscrape.")
            tweets = fetch_latest_tweets_snscrape("FURIA", count=5)
            users = {}
        except Exception as e:
            st.sidebar.error(f"Erro ao carregar tweets: {e}")
            tweets = []
            users = {}
    else:
        st.sidebar.warning("🔒 Bearer token do Twitter não configurado")
        tweets = []
        users = {}

    if not tweets:
        st.sidebar.info("⚠️ Nenhum tweet recente encontrado.")
    else:
        for t in tweets:
            # data e texto
            ts = t.created_at.strftime("%d/%m/%Y %H:%M") if hasattr(t, 'created_at') else ''
            text = t.text if hasattr(t, 'text') else getattr(t, 'content', '')
            # obtém usuário a partir do map
            user = users.get(t.author_id) if users else None

            # monta HTML do card
            text_html = text.replace("\n", "<br>")
            avatar_url = user.profile_image_url if user and hasattr(user, 'profile_image_url') else None
            name = user.name if user and hasattr(user, 'name') else ''
            handle = '@' + user.username if user and hasattr(user, 'username') else ''

            tweet_html = '<div class="tweet-card">'
            tweet_html += '<div class="tweet-header">'
            if avatar_url:
                tweet_html += f'<img src="{avatar_url}" class="tweet-avatar"/>'
            tweet_html += f'<span class="tweet-user">{name}</span>'
            tweet_html += f'<span class="tweet-handle">{handle}</span>'
            tweet_html += f'<span class="tweet-time">{ts}</span>'
            tweet_html += '</div>'
            tweet_html += f'<div class="tweet-text">{text_html}</div>'
            tweet_html += '</div>'

            st.sidebar.markdown(tweet_html, unsafe_allow_html=True)

    # Wizard state e demais passos (mantidos do seu código original)
    if 'step' not in st.session_state:
        st.session_state.step = 1
    steps = ["Dados Básicos 📋", "Documento 📑", "Redes Sociais 🔗", "Links eSports 🌐", "Extras 🎁", "Resumo 🎉"]
    st.sidebar.progress((st.session_state.step-1)/(len(steps)-1))

    def next_step(valid=True):
        if valid:
            st.session_state.step = min(st.session_state.step+1, len(steps))
    def prev_step():
        st.session_state.step = max(st.session_state.step-1, 1)

    st.title("🐆 Bem-vindo, FURIA Lover!")
    st.write("Preencha seu perfil e conquiste **badges** exclusivos! 🌟")

    # Step 1: Dados Básicos (Obrigatórios)
    if st.session_state.step == 1:
        with st.form("basic_info"):
            name = st.text_input("🖋️ Nome completo *", key='name')
            birth = st.text_input("🎂 Data de nascimento *", key='birthdate', placeholder='DD/MM/AAAA')
            address = st.text_input("🏠 Endereço *", key='address')
            cpf = st.text_input("🔒 CPF *", key='cpf')
            interests = st.multiselect("🎮 Interesses *", ["FURIA","CS:GO","LoL","VALORANT","R6 Siege","Outro"], key='interests')
            activities = st.text_area("✨ Atividades/Eventos (último ano) *", key='activities')
            purchases = st.text_area("🛍️ Compras & Merch (último ano) *", key='purchases')
            submitted = st.form_submit_button("Continuar")
            if submitted:
                missing = []
                for var,label in [(name,'nome'),(birth,'nascimento'),(address,'endereço'),(cpf,'cpf'),(interests,'interesses'),(activities,'atividades'),(purchases,'compras')]:
                    if not var:
                        missing.append(label)
                if missing:
                    st.error(f"Preencha: {', '.join(missing)} 🚨")
                else:
                    next_step()

    # Step 2: Documento (Obrigatório)
    elif st.session_state.step == 2:
        st.subheader("📑 Upload de Documento *")
        uploaded = st.file_uploader("Envie RG/CNH:", type=['png','jpg','jpeg'], key='doc')
        ok = False
        if uploaded:
            img = Image.open(uploaded)
            st.image(img, use_column_width=True)
            if validate_document(uploaded.read()):
                st.success("✅ Documento validado!")
                ok = True
            else:
                st.error("🚫 Falha na validação.")
        cols = st.columns(3)
        if cols[0].button("Voltar"): prev_step()
        if cols[2].button("Continuar"):
            if ok:
                next_step()
            else:
                st.error("Documento **obrigatório**")

    # Step 3: Redes Sociais (Opcional)
    elif st.session_state.step == 3:
        st.subheader("🔗 Redes Sociais (Opcional)")

        twitter_handle = st.text_input("📱 Seu usuário no Twitter (sem @)", key='twitter_handle')
        tweets = []

        if twitter_handle:
            # Tenta via API oficial
            try:
                tweets = fetch_user_furia_interactions(
                    twitter_api_key=os.getenv("TW_API_KEY"),
                    twitter_api_secret=os.getenv("TW_API_SECRET"),
                    twitter_token=os.getenv("TW_TOKEN"),
                    twitter_token_secret=os.getenv("TW_TOKEN_SECRET"),
                    username=twitter_handle,
                    max_tweets=50
                )
            except Exception as e:
                msg = str(e)
                if "403" in msg or "Forbidden" in msg:
                    st.info("🔄 API bloqueada, fazendo fallback com snscrape...")
                    tweets = fetch_latest_tweets_snscrape(twitter_handle, count=50)
                else:
                    st.warning(f"Não foi possível buscar tweets: {e}")

            # Exibe resultados (pode vir de Tweepy ou snscrape)
            if tweets:
                st.markdown("**Menções suas à FURIA nos últimos 50 tweets:**")
                for t in tweets:
                    text = getattr(t, 'full_text', None) or getattr(t, 'content', '')
                    date = getattr(t, 'created_at', None) or getattr(t, 'date', None)
                    st.write(f"- {date}: {text}")

        cols = st.columns(3)
        if cols[0].button("Voltar"):
            prev_step()
        if cols[2].button("Continuar"):
            next_step()

    # Step 4: Links eSports (Obrigatório)
    elif st.session_state.step == 4:
        st.subheader("🌐 Links eSports *")
        link = st.text_input("⛹️‍♂️ Liquipedia/HLTV/gosu.gg:", key='esports_link')
        relevant = False
        if link:
            try:
                # cria um resumo básico do perfil
                summary = f"{st.session_state.name}, interesses: {', '.join(st.session_state.interests)}"
                relevant = validate_esports_link(
                    openai_api_key=os.getenv("OPENAI_KEY"),
                    url=link,
                    user_profile_summary=summary
                )
                if relevant:
                    st.success("✅ Link relevante ao seu perfil!")
                else:
                    st.error("🚫 Este link não parece corresponder ao seu perfil.")
            except Exception as e:
                st.warning(f"Erro ao validar link: {e}")

        cols = st.columns(3)
        if cols[0].button("Voltar"): prev_step()
        if cols[2].button("Continuar"):
            if relevant:
                next_step()
            else:
                st.error("Link **obrigatório** e relevante 🚨")

    # Step 5: Extras (Opcional)
    elif st.session_state.step == 5:
        st.subheader("🎁 Extras FURIA (Opcional)")
        st.text_input("🏆 Jogador favorito:", key='fav_player')
        st.slider("⏳ Anos como fã", 0, 10, key='fan_years')
        cols = st.columns(3)
        if cols[0].button("Voltar"): prev_step()
        if cols[2].button("Continuar"): next_step()

    # Step 6: Resumo
    else:
        st.subheader("🎉 Resumo do Seu Perfil")
        for k,v in st.session_state.items():
            if k != 'step':
                st.write(f"**{k.replace('_',' ').title()}:** {v}")
        if st.button("✅ Salvar e Finalizar"):
            c.execute(
                "INSERT INTO fans (name, address, cpf, interests, activities, purchases, social_profiles, esports_profiles, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    st.session_state.name,
                    st.session_state.address,
                    st.session_state.cpf,
                    ','.join(st.session_state.interests),
                    st.session_state.activities,
                    st.session_state.purchases,
                    ';'.join([f"{p}:{st.session_state[p.lower()]}" for p in ['Twitter','Instagram','Facebook','TikTok'] if st.session_state.get(p.lower())]),
                    st.session_state.esports_link,
                    datetime.utcnow().isoformat()
                )
            )
            conn.commit()
            st.balloons()
            st.success("🎊 Perfil salvo com sucesso! Obrigado por ser FURIA! 🐆")

# --- Modo Admin ---
elif mode.startswith('Admin'):
    pwd = st.sidebar.text_input("🔑 Senha Admin:", type='password')
    if pwd != ADMIN_PASSWORD:
        st.error("🔐 Senha incorreta")
    else:
        st.title("📊 Dashboard de Fãs FURIA")
        df = pd.read_sql_query("SELECT * FROM fans", conn)
        st.metric("Total de Fãs cadastrados", len(df))
        st.subheader("🎮 Distribuição de Interesses")
        ints = df['interests'].str.get_dummies(sep=',').sum().sort_values(ascending=False)
        st.bar_chart(ints)
        if 'fan_years' in df.columns:
            st.subheader("⏳ Anos como Fã")
            years = df['fan_years'].dropna().astype(int).value_counts().sort_index()
            st.bar_chart(years)
        st.subheader("✨ Atividades/Eventos")
        st.text_area("", '\n'.join(df['activities']), height=150)
        st.subheader("📝 Dados Cadastrais")
        st.dataframe(df)
        st.download_button("📥 Exportar CSV", df.to_csv(index=False), "fura_fans.csv")
