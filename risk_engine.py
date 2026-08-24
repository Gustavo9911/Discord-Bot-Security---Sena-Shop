from datetime import datetime, timezone
from config import RISK_SCORES


def calculate_risk(member, invite_data=None, previous_joins=0, same_inviter_recent=0) -> tuple[int, str, list]:
    """
    Calcula a pontuação de risco de um membro.
    Retorna: (score, level, lista de razões)
    """
    score = 0
    reasons = []

    created = member.created_at
    now = datetime.now(timezone.utc)
    age_days = (now - created).days

    # Idade da conta
    if age_days < 1:
        score += RISK_SCORES["account_age_under_1d"]
        reasons.append(f"Conta com menos de 1 dia ({age_days}d)")
    elif age_days < 3:
        score += RISK_SCORES["account_age_under_3d"]
        reasons.append(f"Conta com menos de 3 dias ({age_days}d)")
    elif age_days < 7:
        score += RISK_SCORES["account_age_under_7d"]
        reasons.append(f"Conta com menos de 7 dias ({age_days}d)")
    elif age_days < 30:
        score += RISK_SCORES["account_age_under_30d"]
        reasons.append(f"Conta com menos de 30 dias ({age_days}d)")

    # Avatar padrão
    if member.avatar is None:
        score += RISK_SCORES["default_avatar"]
        reasons.append("Avatar padrão")

    # Banner
    if getattr(member, "banner", None) is None:
        score += RISK_SCORES["no_banner"]

    # Já esteve no servidor
    if previous_joins > 0:
        score += RISK_SCORES["previous_join"]
        reasons.append(f"Já entrou {previous_joins} vez(es) anteriormente")

    # Mesmo convidador trazendo várias contas novas em pouco tempo
    if same_inviter_recent >= 3:
        score += RISK_SCORES["multiple_accounts_same_inviter_short_time"]
        reasons.append(f"Convidador trouxe {same_inviter_recent} contas novas recentemente")

    # Username suspeito
    name_lower = member.name.lower()
    if name_lower.startswith("user") or len(member.name) <= 3:
        score += RISK_SCORES["suspicious_username"]
        reasons.append("Username suspeito/genérico")

    # Convite temporário
    if invite_data and invite_data.get("temporary"):
        score += 15
        reasons.append("Convite temporário")

    # Classificação
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "moderate"
    else:
        level = "low"

    return score, level, reasons
