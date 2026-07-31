from flask import Flask, abort, send_from_directory
import os
from waitress import serve
import logging
import threading
import multiprocessing
from pathlib import Path

from nulspec_nominations import register_nulspec_nomination_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate environment variables
required_env_vars = [
    'ANTHROPIC_API_KEY', 'CLAUDE_BOT_TOKEN', 'TOMMY_BOT_TOKEN',
    'BOB_BOT_TOKEN', 'GEORGE_BOT_TOKEN'
]

for var in required_env_vars:
    if not os.environ.get(var):
        logger.warning(f"Missing environment variable: {var}")

BOT_STATUS_NAMES = {
    'tommy': 'Tommy',
    'bob': 'Bob',
    'claude': 'Claude',
    'george': 'Kevin the Klanker',
    'kevin': 'Kevin the Klanker',
    'kevin-the-klanker': 'Kevin the Klanker',
    'klanker': 'Kevin the Klanker',
}
VALID_BOTS = set(BOT_STATUS_NAMES)
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_STORAGE_DIR = (BASE_DIR / "downloads").resolve()
DOWNLOAD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def create_app():
    app = Flask("bot_server")

    @app.route('/<bot_name>')
    def bot_route(bot_name):
        normalized_bot_name = bot_name.lower()
        if normalized_bot_name not in VALID_BOTS:
            abort(404)
        return f"Hello. I am {BOT_STATUS_NAMES[normalized_bot_name]} and I am alive!"

    @app.route('/')
    def home():
        return "Bot server running! All systems operational.", 200

    @app.route('/health')
    def health_check():
        return "OK", 200

    @app.route('/downloads/<path:filename>')
    def serve_download(filename):
        logger.info("Download request for %s", filename)
        try:
            target_path = (DOWNLOAD_STORAGE_DIR / filename).resolve()
        except (OSError, RuntimeError) as exc:
            logger.warning("Failed to resolve download path for %s: %s", filename, exc)
            abort(404)

        if not target_path.exists() or not target_path.is_file():
            logger.warning("Download file %s not found under %s", target_path, DOWNLOAD_STORAGE_DIR)
            abort(404)
        try:
            if not target_path.is_relative_to(DOWNLOAD_STORAGE_DIR):
                logger.warning("Blocked download outside root: %s", target_path)
                abort(404)
        except AttributeError:
            # For Python versions without is_relative_to (fallback)
            if DOWNLOAD_STORAGE_DIR not in target_path.parents:
                logger.warning("Blocked download outside root: %s", target_path)
                abort(404)

        return send_from_directory(DOWNLOAD_STORAGE_DIR, filename, as_attachment=True)

    register_nulspec_nomination_routes(app)
    return app


def run_server():
    """Run the Flask server with waitress"""
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '127.0.0.1')
    app = create_app()
    logger.info(f"Starting bot server on port {port}")
    logger.info(f"Access bots at: http://{host}:{port}/<bot_name>")

    # Start server
    serve(app, host=host, port=port, url_scheme='http', threads=4)


def start_bot_process():
    """Start the main bot process"""
    # Import here to avoid circular imports
    from main import main
    import asyncio

    logger.info("Starting bot process")
    try:
        # Run the main function in a separate process
        bot_process = multiprocessing.Process(
            target=lambda: asyncio.run(main()),
            daemon=True
        )
        bot_process.start()
        logger.info(f"Bot process started with PID: {bot_process.pid}")
        return bot_process
    except Exception as e:
        logger.error(f"Failed to start bot process: {e}")
        return None


if __name__ == "__main__":
    # Only start the bot process if this is the main entry point
    # For deployment, run only the loopback health/download server by default.
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '127.0.0.1')
    logger.info(f"Starting server on {host}:{port}")
    app = create_app()
    serve(app, host=host, port=port, url_scheme='http', threads=4)
