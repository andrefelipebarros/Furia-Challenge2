import sqlite3
from datetime import datetime, timezone

# Conexão com o banco de dados
conn = sqlite3.connect('knowyourfan.db')
c = conn.cursor()

# Cria a tabela caso não exista e garante estrutura básica
c.execute('''
CREATE TABLE IF NOT EXISTS fans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    address TEXT,
    cpf TEXT,
    interests TEXT,
    activities TEXT,
    purchases TEXT
)
''')
conn.commit()

# Garante que as colunas adicionais existem
def ensure_columns_exist():
    for column, col_type in [
        ("social_profiles", "TEXT"),
        ("esports_profiles", "TEXT"),
        ("created_at", "TEXT")
    ]:
        try:
            c.execute(f"ALTER TABLE fans ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass  # já existe

# Executa a verificação/adição das colunas
ensure_columns_exist()
conn.commit()

# Novos dados fictícios para inserir
fans = [
    {
        "name": "Mariana Rocha",
        "address": "Rua das Lendas, 123, Recife, PE",
        "cpf": "111.222.333-44",
        "interests": "FURIA,VALORANT,LoL",
        "activities": "Organizou campeonato amador de VALORANT na sua cidade.",
        "purchases": "Camiseta autografada da FURIA, mouse gamer.",
        "social_profiles": "Twitter:https://twitter.com/mari_rocha;Instagram:https://instagram.com/mari_rocha",
        "esports_profiles": "https://liquipedia.net/valorant/Mariana_Rocha",
    },
    {
        "name": "Felipe Santos",
        "address": "Avenida Central, 500, Porto Alegre, RS",
        "cpf": "555.666.777-88",
        "interests": "CS:GO,FURIA,R6 Siege",
        "activities": "Participou de watch party da FURIA no último Major.",
        "purchases": "Boné oficial da FURIA, assinatura premium Discord.",
        "social_profiles": "Facebook:https://facebook.com/felipe.gg;TikTok:https://tiktok.com/@felipeplays",
        "esports_profiles": "https://www.hltv.org/player/54321/felipe_santos",
    },
    {
        "name": "Carla Menezes",
        "address": "Travessa Esportiva, 77, Salvador, BA",
        "cpf": "999.000.111-22",
        "interests": "FIFA,FURIA,F1",
        "activities": "Participou de torneio de FIFA organizado pela FURIA.",
        "purchases": "Controle customizado, camisa retrô.",
        "social_profiles": "YouTube:https://youtube.com/c/carlamenezes;Instagram:https://instagram.com/carla_menezes",
        "esports_profiles": "https://www.fifa.gg/player/112233/carla_menezes",
    },
    {
        "name": "Rafael Lima",
        "address": "Rua Pixel, 404, Brasília, DF",
        "cpf": "444.333.222-11",
        "interests": "LoL,VALORANT,CS:GO",
        "activities": "Stream semanal de CS:GO com análise de jogos da FURIA.",
        "purchases": "Microfone condensador, headset RGB.",
        "social_profiles": "Twitch:https://twitch.tv/rafaellima;Twitter:https://twitter.com/rlima",
        "esports_profiles": "https://www.vlr.gg/player/33445/rafael_lima",
    },
    {
        "name": "Sofia Almeida",
        "address": "Praça Gamer, 9, Fortaleza, CE",
        "cpf": "777.888.999-00",
        "interests": "R6 Siege,FURIA,Overwatch",
        "activities": "Líder de clã em Rainbow Six Siege e fã da FURIA.",
        "purchases": "Skin exclusiva no jogo, pôster de time.",
        "social_profiles": "Instagram:https://instagram.com/sofia.almeida;Discord:sofia#1234",
        "esports_profiles": "https://siege.gg/players/9988/sofia_almeida",
    }
]

# Inserção no banco
def seed_data():
    for fan in fans:
        c.execute(
            '''
            INSERT INTO fans (name, address, cpf, interests, activities, purchases, social_profiles, esports_profiles, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                fan["name"],
                fan["address"],
                fan["cpf"],
                fan["interests"],
                fan["activities"],
                fan["purchases"],
                fan["social_profiles"],
                fan["esports_profiles"],
                datetime.now(timezone.utc).isoformat()
            )
        )
    conn.commit()

if __name__ == '__main__':
    seed_data()
    conn.close()
    print("✅ Dados inseridos com sucesso.")
