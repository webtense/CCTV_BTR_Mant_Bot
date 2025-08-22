#!/usr/bin/env python3
# CCTV_BTR_Mant_Bot — v1.7.0 · 2025-08-22
import os, shlex, asyncio, textwrap, time, re, subprocess as sp
from datetime import datetime
from pathlib import Path

from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters, ConversationHandler
)

BASE = Path("/opt/CCTV_BTR_Mant_Bot")
ENV  = BASE / ".env"
LOG  = BASE / "bot.log"

# ==== util ====
def getenv(k, default=""):
    v = os.environ.get(k, default)
    if v is None: v = ""
    return v.strip()

def load_env_to_os():
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if not line or line.strip().startswith("#"): continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

def fmt_code(s: str, limit=3800):
    s = s.strip()
    if len(s) > limit:
        s = s[:limit-20] + "\n... (truncado)"
    return f"```\n{s}\n```"

def run(cmd: str, timeout=120):
    # Ejecuta en bash -lc para que funcionen pipelines
    p = sp.run(["bash","-lc",cmd], capture_output=True, text=True, timeout=timeout)
    out = p.stdout.strip()
    err = p.stderr.strip()
    rc  = p.returncode
    return rc, out, err

def human_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def mask_token(tok: str):
    return tok[:9] + "********" if tok else "(vacío)"

def file_exists(p: str):
    return Path(p).exists()

# Carga .env
load_env_to_os()

BOT_TOKEN = getenv("BOT_TOKEN")
CHAT_ID = getenv("CHAT_ID")              # destino por defecto
AUTH_CHAT = getenv("AUTHORIZED_CHAT_ID") # si se fija, sólo ese chat puede usar el bot

CAM_DIR = getenv("CAM_DIR","/CAM")
THRESHOLD = getenv("THRESHOLD","90")
TARGET = getenv("TARGET","85")
DAYS = getenv("DAYS","15")
REC_SERVICE = getenv("SERVICE_RECORDER","agentdvr.service")

# Rutas opcionales de scripts “externos”
BTR_BASE = "/opt/btr_bot"
CAM_CLEAN = f"{BTR_BASE}/cam_clean.sh"
STATUS_RPT = f"{BTR_BASE}/cctv_status_report.sh"
TUNEUP = f"{BTR_BASE}/system_tuneup.sh"
AGENT_UPD = "/root/update_agentdvr.sh"

# Estado de confirmaciones
PEND = {}   # key: chat_id -> {"action":str, "args":tuple, "ts":float}

def allowed(update: Update) -> bool:
    if not AUTH_CHAT:
        return True
    return str(update.effective_chat.id) == AUTH_CHAT

async def reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("⛔ Este chat no está autorizado. Ajusta AUTHORIZED_CHAT_ID en .env y reinicia el servicio.")

# ==== comandos simples ====
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await reject(update, ctx)
    txt = textwrap.dedent(f"""
    👋 *CCTV BTR Mant Bot* en {os.uname().nodename}
    Usa /help para ver todas las órdenes.
    """)
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await reject(update, ctx)
    txt = textwrap.dedent("""
    *Comandos disponibles*
    /ping – latencia y hora
    /whoami – IDs del chat y del bot
    /estado – resumen sistema y /CAM
    /limpiar – limpieza inteligente (edad + objetivo)
    /limpiar_emergencia – limpieza más agresiva
    /tuneup – puesta a punto del sistema
    /reiniciar_rec – reinicia el servicio de grabación
    /actualizar_agentdvr – ejecuta /root/update_agentdvr.sh si existe
    /programar_informe HH:MM – programa informe diario
    /programar_limpieza hourly|HH:MM – programa limpieza
    /log [N] – últimas N líneas del log del bot (def. 50)
    /version – versión del bot
    /setchat – guarda este chat como CHAT_ID en .env
    /env – muestra variables (token ofuscado)
    """)
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await reject(update, ctx)
    t0 = time.perf_counter()
    m = await update.message.reply_text("🏓 Pong…")
    dt = (time.perf_counter()-t0)*1000
    await m.edit_text(f"🏓 {dt:.0f} ms · {human_ts()}")

async def whoami(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await reject(update, ctx)
    me = await ctx.bot.get_me()
    ch = update.effective_chat
    txt = f"""👤 *Yo*: @{me.username} ({me.id})
💬 *Chat*: {ch.title or ch.full_name} ({ch.id})
"""
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

# ==== estado ====
async def estado(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await reject(update, ctx)
    # Si existe script externo, úsalo y adjunta salida
    if file_exists(STATUS_RPT):
        rc, out, err = run(shlex.quote(STATUS_RPT) + " | sed -n '1,200p'")
        body = out or err or "(sin salida)"
        await update.message.reply_markdown(fmt_code(body))
        return
    # Inline
    cmds = [
        "hostnamectl --static || hostname",
        "uptime -p || true",
        "uname -r",
        f"free -h | awk '/Mem:/{'{print $3\"/\"$2}'}'",
        "df -hP / | awk 'NR==2{print $5\" (\"$3\"/\"$2\")\"}'",
        f"df -hP {shlex.quote(CAM_DIR)} | awk 'NR==2{{print $5\" (\"$3\"/\"$2\")\"}}' || echo 'n/a'",
        f"systemctl is-active {shlex.quote(REC_SERVICE)} || echo unknown",
    ]
    labels = ["Host","Uptime","Kernel","RAM","/","CAM",REC_SERVICE]
    rows=[]
    for lab, cmd in zip(labels, cmds):
        rc,out,err = run(cmd, timeout=10)
        rows.append(f"{lab:>8}: {out.strip() if out else err.strip()}")
    await update.message.reply_markdown(fmt_code("\n".join(rows)))

# ==== confirmaciones ====
async def ask_confirm(update: Update, action: str, *args):
    PEND[update.effective_chat.id] = {"action":action, "args":args, "ts":time.time()}
    await update.message.reply_text(
        f"¿Confirmas *{action}*? Responde `sí` o `no` en 60s.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ForceReply(selective=True)
    )

async def confirm_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Respuesta libre: sólo si hay algo pendiente
    pend = PEND.get(update.effective_chat.id)
    if not pend: return
    if time.time() - pend["ts"] > 60:
        PEND.pop(update.effective_chat.id, None)
        return await update.message.reply_text("⏱️ Confirmación expirada.")
    if update.message.text.strip().lower() not in ("si","sí","s","yes","y"):
        PEND.pop(update.effective_chat.id, None)
        return await update.message.reply_text("❎ Cancelado.")
    action = pend["action"]; args = pend["args"]
    PEND.pop(update.effective_chat.id, None)
    # Ejecuta acción confirmada
    if action == "limpieza":
        await do_limpieza(update, ctx, emergency=False)
    elif action == "limpieza_emergencia":
        await do_limpieza(update, ctx, emergency=True)
    elif action == "tuneup":
        await do_tuneup(update, ctx)
    elif action == "reiniciar_rec":
        await do_restart_rec(update, ctx)
    elif action == "actualizar_agentdvr":
        await do_update_agent(update, ctx)
    elif action == "programar_informe":
        await do_prog_informe(update, ctx, *args)
    elif action == "programar_limpieza":
        await do_prog_limpieza(update, ctx, *args)

# ==== acciones ====
async def do_limpieza(update, ctx, emergency=False):
    if file_exists(CAM_CLEAN):
        env = os.environ.copy()
        if emergency:
            env["THRESHOLD"]="1"; env["TARGET"]="50"
        rc, out, err = run(shlex.quote(CAM_CLEAN), timeout=600)
        text = out or err or "(sin salida)"
        return await update.message.reply_markdown(fmt_code(text))
    # Inline (sin script externo)
    if emergency:
        cmd = f"""
        DAYS={shlex.quote(DAYS)} CAM_DIR={shlex.quote(CAM_DIR)} TARGET=50 THRESHOLD=1
        find "{CAM_DIR}" -type f -mtime +{DAYS} -print -delete 2>/dev/null | wc -l
        """
    else:
        cmd = f"""
        DAYS={shlex.quote(DAYS)} CAM_DIR={shlex.quote(CAM_DIR)}
        find "{CAM_DIR}" -type f -mtime +{DAYS} -print -delete 2>/dev/null | wc -l
        """
    rc,out,err = run(cmd, timeout=600)
    await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))

async def do_tuneup(update, ctx):
    if file_exists(TUNEUP):
        rc,out,err = run(shlex.quote(TUNEUP), timeout=1200)
        return await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))
    cmd = """
    find /tmp -mindepth 1 -maxdepth 1 -mtime +1 -print -exec rm -rf {} + || true
    journalctl --vacuum-time=14d || true
    if command -v docker >/dev/null 2>&1; then docker system prune -af || true; fi
    if command -v apt-get >/dev/null 2>&1; then apt-get update -y && apt-get -o Dpkg::Options::=--force-confnew dist-upgrade -y && apt-get autoremove -y && apt-get clean || true; fi
    echo "Puesta a punto terminada."
    """
    rc,out,err = run(cmd, timeout=1800)
    await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))

async def do_restart_rec(update, ctx):
    rc,out,err = run(f"systemctl restart {shlex.quote(REC_SERVICE)} && sleep 1 && systemctl is-active {shlex.quote(REC_SERVICE)}", timeout=30)
    await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))

async def do_update_agent(update, ctx):
    if not file_exists(AGENT_UPD):
        return await update.message.reply_text("No existe /root/update_agentdvr.sh")
    rc,out,err = run(shlex.quote(AGENT_UPD), timeout=1800)
    await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))

async def do_prog_informe(update, ctx, hhmm: str):
    # Reescribe timer OnCalendar=*-*-* HH:MM:00
    if not re.fullmatch(r"\d{2}:\d{2}", hhmm):
        return await update.message.reply_text("Formato inválido. Ejemplo: /programar_informe 07:45")
    unit = "/etc/systemd/system/cctv-status-report.timer"
    new = f"""[Unit]
Description=Programación informe de estado CCTV ({hhmm})

[Timer]
OnCalendar=*-*-* {hhmm}:00
Persistent=true

[Install]
WantedBy=timers.target
"""
    (Path(unit)).write_text(new)
    rc,out,err = run("systemctl daemon-reload && systemctl enable --now cctv-status-report.timer && systemctl list-timers --all | grep cctv-status-report || true", timeout=20)
    await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))

async def do_prog_limpieza(update, ctx, arg: str):
    if arg == "hourly":
        rc,out,err = run("systemctl enable --now cam-clean.timer && systemctl list-timers --all | grep cam-clean || true", timeout=20)
        return await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))
    if not re.fullmatch(r"\d{2}:\d{2}", arg):
        return await update.message.reply_text("Usa 'hourly' o HH:MM. Ej: /programar_limpieza 07:30")
    unit = "/etc/systemd/system/cam-clean-0730.timer"
    new = f"""[Unit]
Description=Limpieza /CAM diaria {arg}

[Timer]
OnCalendar=*-*-* {arg}:00
Persistent=true

[Install]
WantedBy=timers.target
"""
    (Path(unit)).write_text(new)
    rc,out,err = run("systemctl daemon-reload && systemctl enable --now cam-clean-0730.timer && systemctl list-timers --all | egrep 'cam-clean|cctv-status' || true", timeout=20)
    await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))

async def log_cmd(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    n = 50
    if ctx.args and ctx.args[0].isdigit():
        n = int(ctx.args[0])
    rc,out,err = run(f"journalctl -u cctv-maint-bot -n {n} --no-pager")
    await update.message.reply_markdown(fmt_code(out or err or "(sin salida)"))

async def version(update, ctx):
    await update.message.reply_text("CCTV_BTR_Mant_Bot v1.7.0 · 2025-08-22")

async def env_cmd(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    tok = getenv("BOT_TOKEN")
    out = f"""Variables:
BOT_TOKEN={mask_token(tok)}
CHAT_ID={getenv('CHAT_ID')}
AUTHORIZED_CHAT_ID={getenv('AUTHORIZED_CHAT_ID')}
CAM_DIR={CAM_DIR}  THRESHOLD={THRESHOLD}  TARGET={TARGET}  DAYS={DAYS}
SERVICE_RECORDER={REC_SERVICE}
"""
    await update.message.reply_markdown(fmt_code(out, limit=1200))

async def setchat(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    cid = update.effective_chat.id
    # Escribe CHAT_ID en .env
    lines=[]
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if line.startswith("CHAT_ID="): continue
            lines.append(line)
    lines.append(f"CHAT_ID={cid}")
    ENV.write_text("\n".join(lines) + "\n")
    await update.message.reply_text(f"✅ Guardado CHAT_ID={cid} en {ENV}. Recarga servicio para aplicar.")

# ==== wrappers de comandos “confirmables” ====
async def limpiar(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    await ask_confirm(update, "limpieza")

async def limpiar_emerg(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    await ask_confirm(update, "limpieza_emergencia")

async def tuneup(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    await ask_confirm(update, "tuneup")

async def reiniciar_rec(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    await ask_confirm(update, "reiniciar_rec")

async def actualizar_agent(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    await ask_confirm(update, "actualizar_agentdvr")

async def programar_informe(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    if not ctx.args: return await update.message.reply_text("Uso: /programar_informe HH:MM")
    await ask_confirm(update, "programar_informe", ctx.args[0])

async def programar_limpieza(update, ctx):
    if not allowed(update): return await reject(update, ctx)
    if not ctx.args: return await update.message.reply_text("Uso: /programar_limpieza hourly|HH:MM")
    await ask_confirm(update, "programar_limpieza", ctx.args[0])

# ==== main ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("estado", estado))

    app.add_handler(CommandHandler("limpiar", limpiar))
    app.add_handler(CommandHandler("limpiar_emergencia", limpiar_emerg))
    app.add_handler(CommandHandler("tuneup", tuneup))
    app.add_handler(CommandHandler("reiniciar_rec", reiniciar_rec))
    app.add_handler(CommandHandler("actualizar_agentdvr", actualizar_agent))

    app.add_handler(CommandHandler("programar_informe", programar_informe))
    app.add_handler(CommandHandler("programar_limpieza", programar_limpieza))
    app.add_handler(CommandHandler("log", log_cmd))
    app.add_handler(CommandHandler("version", version))
    app.add_handler(CommandHandler("env", env_cmd))
    app.add_handler(CommandHandler("setchat", setchat))

    # Confirmaciones (sí/no) sólo cuando hay pendiente
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), confirm_reply))

    # Ejecuta en modo polling (sencillo para systemd)
    app.run_polling(allowed_updates=None, close_loop=False)

if __name__ == "__main__":
    main()
