import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))

# IDs de canais e cargos (preencha no .env)
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
VERIFY_CHANNEL_ID = int(os.getenv("VERIFY_CHANNEL_ID", 0))
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", 0))

# Nomes dos cargos do sistema
ROLE_PENDING = "🔍 Verificação Pendente"
ROLE_VERIFIED = "✅ Verificado"
ROLE_ANALYSIS = "⚠️ Em Análise"
ROLE_BLOCKED = "🚫 Bloqueado"

# Configurações de risco
MIN_ACCOUNT_AGE_DAYS = 7
MIN_STAY_DAYS_FOR_VALID = 3
HIGH_RISK_THRESHOLD = 70
MODERATE_RISK_THRESHOLD = 40

# Pontuação de risco (ajustável)
RISK_SCORES = {
    "account_age_under_1d": 40,
    "account_age_under_3d": 25,
    "account_age_under_7d": 15,
    "account_age_under_30d": 8,
    "default_avatar": 12,
    "no_banner": 5,
    "previous_join": 20,
    "rejoin_same_invite": 25,
    "multiple_accounts_same_inviter_short_time": 30,
    "invite_invalid_or_expired": 50,
    "suspicious_username": 10,
}
