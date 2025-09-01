import requests
from typing import Optional
from .logger import get_logger

logger = get_logger("notifier")

class Notifier:
    def __init__(self, token: Optional[str], chat_id: Optional[str]):
        self.token = token
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        if not self.token or not self.chat_id:
            logger.debug(f"[NO-TELEGRAM] {text}")
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            resp = requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Telegram error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Error sending Telegram message: {e}")

    def heartbeat(self) -> None:
        self.send("✅ Bot activo (heartbeat)")

    def trade_open(self, symbol: str, side: str, qty: float, entry: float, tp: float, sl: float) -> None:
        self.send(
            f"🟢 <b>Abrir operación</b>\n"
            f"Símbolo: {symbol}\n"
            f"Lado: {side}\n"
            f"Cantidad: {qty}\n"
            f"Entrada: {entry}\n"
            f"TP: {tp}\n"
            f"SL: {sl}"
        )

    def trade_close(self, symbol: str, side: str, qty: float, exit_price: float, reason: str) -> None:
        self.send(
            f"🔴 <b>Cerrar operación</b>\n"
            f"Símbolo: {symbol}\n"
            f"Lado cerrado: {side}\n"
            f"Cantidad: {qty}\n"
            f"Precio salida: {exit_price}\n"
            f"Motivo: {reason}"
        )

    def error(self, message: str) -> None:
        self.send(f"⚠️ Error: {message}")
