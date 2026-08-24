# 🔐 Discord Security Bot – Verificação + Convites + Anti-Alt

Sistema completo de verificação de membros, rastreamento avançado de convites e detecção de contas suspeitas (fakes/alts/bots).

## ✨ Funcionalidades

- **Verificação de novos membros** com pontuação de risco multi-sinais
- **Criação automática** dos cargos:
  - 🔍 Verificação Pendente
  - ✅ Verificado
  - ⚠️ Em Análise
  - 🚫 Bloqueado
- **Rastreamento de convites** (quem convidou quem)
- **Contagem apenas de convites válidos** (evita farm de alts)
- **Anti-bypass** (reentradas, múltiplas contas, etc.)
- **Logs detalhados** em canal privado da staff
- **Comandos slash** para a equipe:
  - `/verificar` – aprovar / rejeitar / colocar em análise
  - `/info` – informações de segurança do membro
  - `/ranking` – ranking de convites válidos
  - `/meus-convites` – qualquer membro pode ver seus convites

## 📋 Requisitos

- Python 3.10 ou superior
- Bot com as seguintes **Intents** ativadas no Developer Portal:
  - Server Members Intent
  - Message Content Intent (opcional)
- Permissões do bot:
  - Gerenciar Cargos
  - Expulsar Membros (opcional)
  - Ver Audit Log / Ver Convites
  - Enviar Mensagens + Embeds

## 🚀 Instalação

1. Extraia o ZIP
2. Crie um ambiente virtual (recomendado):
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux / macOS
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Copie o arquivo de exemplo e preencha:
   ```bash
   cp .env.example .env
   ```
5. Edite o `.env` com seu token e IDs
6. Inicie o bot:
   ```bash
   python bot.py
   ```

## ⚙️ Configuração do Servidor

1. Coloque o cargo do bot **acima** dos cargos que ele cria
2. Crie um canal de logs privado (só staff) e coloque o ID no `.env`
3. Configure as permissões de canais:
   - `@everyone` → **não** vê os canais principais
   - `🔍 Verificação Pendente` → só vê o canal de verificação
   - `✅ Verificado` → acesso normal ao servidor

## 🛡️ Como funciona o risco

O bot analisa vários sinais:

| Sinal                        | Pontos |
|-----------------------------|--------|
| Conta < 1 dia               | +40    |
| Conta < 3 dias              | +25    |
| Conta < 7 dias              | +15    |
| Conta < 30 dias             | +8     |
| Avatar padrão               | +12    |
| Já esteve no servidor       | +20    |
| Mesmo inviter com várias contas novas | +30 |
| Username genérico           | +10    |

- **🟢 Baixo** (< 40) → Verificação Pendente
- **🟡 Moderado** (40-69) → Verificação Pendente
- **🔴 Alto** (≥ 70) → Em Análise (staff decide)

## 📁 Estrutura

```
discord-security-bot/
├── bot.py
├── config.py
├── database.py
├── risk_engine.py
├── invite_tracker.py
├── verification.py
├── roles.py
├── commands/
│   └── staff.py
├── requirements.txt
├── .env.example
└── README.md
```

## ⚠️ Limitações

- O Discord **não** informa diretamente qual convite foi usado. O bot compara o cache de usos.
- Detecção de alt é baseada em heurísticas (idade, avatar, padrões). Para fingerprinting real use serviços externos.
- Vanity URL e alguns convites temporários de 1 uso podem não ser rastreados perfeitamente.

## 📝 Licença

Uso livre. Modifique conforme a necessidade do seu servidor.
