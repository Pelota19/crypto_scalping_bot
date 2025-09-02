# Crypto Scalping Bot Moderno

Bot de trading de alta frecuencia para scalping, diseñado con una arquitectura moderna, segura y modular.

## Características

- **Seguridad:** Manejo de credenciales de API a través de variables de entorno (`.env`).
- **Configurable:** Parámetros de la estrategia (par, timeframe, indicadores) totalmente configurables desde `settings.json`.
- **Asíncrono:** Construido con `asyncio` para un rendimiento y concurrencia óptimos.
- **Robusto:** Logging profesional de eventos y manejo de errores específico del exchange.
- **Modular:** Lógica de estrategia y ejecución desacoplada para fácil mantenimiento.

## Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/Pelota19/crypto_scalping_bot.git
    cd crypto_scalping_bot
    ```

2.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuración

1.  **Crea tu archivo de entorno:**
    Copia el archivo `.env.example` y renómbralo a `.env`.
    ```bash
    cp .env.example .env
    ```
    Edita el archivo `.env` y añade tus claves de API y datos de Telegram.

2.  **Ajusta la estrategia:**
    Modifica el archivo `settings.json` para definir tu par de trading, timeframe y parámetros de los indicadores.

## Uso

Para iniciar el bot, ejecuta:
```bash
python bot.py
```