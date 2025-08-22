# CCTV_BTR_Mant_Bot

Bot de mantenimiento para CCTV con Telegram.

## Requisitos
- Ubuntu 22.04+
- Python 3.10+
- (Opcional) Virtualenv
- Token de Telegram y chat_id (supergrupo: empieza por -100)

## Instalación rápida
```bash
cd /opt/CCTV_BTR_Mant_Bot
cp .env.example .env   # o edita tu .env
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
sudo systemctl enable --now cctv-maint-bot.service
