import asyncio
from playwright.async_api import async_playwright, Error as PlaywrightError
import smtplib
from email.message import EmailMessage
import time
from datetime import datetime

# ==============================================================================
#                      I. CONFIGURACIÓN DEL PRODUCTO Y RASTREO
# ==============================================================================
PRODUCT_URL = "https://www.zara.com/es/es/jersey-punto-lazo-p03920940.html?v1=484707602"
TALLA_BUSCADA = "S"

# SELECTOR DE TALLA: Búsqueda simple por texto.
TALLA_SELECTOR = f'button:has-text("{TALLA_BUSCADA}")'

# SELECTOR DEL BOTÓN INICIAL ("Añadir")
BUTTON_OPEN_SELECTOR = "xpath=//button[contains(translate(normalize-space(.), 'AÑADIR', 'añadir'), 'añadir')]"

# SELECTOR DE COOKIES
COOKIES_SELECTOR = 'button:has-text("Aceptar")'

# Tiempos de espera
TIMEOUT_MS = 20000
INTERVALO_BUSQUEDA_MINUTOS = 15  # Espera si la talla NO está disponible
INTERVALO_POST_ALERTA_HORAS = 12  # Espera si la talla SÍ está disponible (para no spamear)

# ==============================================================================
#                      II. CONFIGURACIÓN DE NOTIFICACIÓN (EMAIL)
# ==============================================================================
SENDER_EMAIL = "tu_email@gmail.com"
APP_PASSWORD = "tu_contraseña_de_aplicación"
RECEIVER_EMAIL = "email_destino@ejemplo.com"


# ==============================================================================


# ------------------------------------------------------------------------------
#                           III. FUNCIONES PRINCIPALES
# ------------------------------------------------------------------------------

def send_email(subject, body):
    """Envía un correo electrónico con codificación UTF-8."""
    try:
        msg = EmailMessage()
        msg.set_content(body, charset='utf-8')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        print("   -> Enviando notificación por email...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
            print("   -> Email enviado con éxito.")
            return True  # Éxito

    except Exception as e:
        print(f"   -> ERROR al enviar el email: {e}")
        return False  # Fallo


async def check_stock_once(p):
    """Realiza una única comprobación de stock."""

    # Crea un navegador nuevo para cada intento
    # ¡MODO HOSTING! headless=True
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    stock_found = False  # Bandera para saber si se encontró stock

    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando comprobación de stock...")

        # 1. Navegación e interacciones iniciales
        await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        # 2. Cookies (No se registra el éxito para evitar spam de logs)
        try:
            await page.click(COOKIES_SELECTOR, timeout=5000)
        except Exception:
            pass

        # 3. Clicar en "Añadir"
        await page.click(BUTTON_OPEN_SELECTOR, timeout=5000)

        # 4. Esperar que la talla esté visible
        print(f"4. Esperando que la talla '{TALLA_BUSCADA}' esté visible...")

        talla_element = page.locator(TALLA_SELECTOR).first
        await talla_element.wait_for(state="visible", timeout=TIMEOUT_MS)

        # 5. VERIFICACIÓN DE DISPONIBILIDAD (INTENTAR CLIC)
        print("5. Verificando disponibilidad intentando hacer clic...")

        await talla_element.click(timeout=3000)

        # 6. ÉXITO (Si el código llega aquí, el clic fue exitoso -> ¡HAY STOCK!)
        stock_found = True
        resultado = f"🎉 STOCK ENCONTRADO: ¡La talla '{TALLA_BUSCADA}' disponible! Revisa YA: {PRODUCT_URL}"
        print(resultado)

        send_email(
            subject=f"[ALERTA ZARA] ¡Stock de talla {TALLA_BUSCADA} encontrado!",
            body=resultado
        )

    except PlaywrightError as e:
        # Fallo del clic por intercepción, deshabilitado o timeout = AGOTADO
        resultado = f"❌ RESULTADO: La talla '{TALLA_BUSCADA}' sigue agotada (Clic bloqueado/Talla no seleccionable)."
        print(resultado)

    except Exception as e:
        # Capturamos cualquier otro error grave (ej: fallo de conexión)
        error_message = f"🛑 Ocurrió un error general en la comprobación: {e}"
        print(error_message)

    finally:
        await browser.close()
        print("Comprobación finalizada.")
        return stock_found  # Devolvemos el estado


async def main_loop():
    """Bucle principal que ejecuta la comprobación continuamente."""
    async with async_playwright() as p:
        while True:
            # Ejecutar una comprobación
            stock_found = await check_stock_once(p)

            if stock_found:
                # Si se encuentra stock, esperar más tiempo para no spamear
                wait_seconds = INTERVALO_POST_ALERTA_HORAS * 3600
                print(f"Stock encontrado. Esperando {INTERVALO_POST_ALERTA_HORAS} horas antes de volver a comprobar.")
            else:
                # Si no se encuentra stock, esperar 15 minutos
                wait_seconds = INTERVALO_BUSQUEDA_MINUTOS * 60
                print(f"Stock agotado. Esperando {INTERVALO_BUSQUEDA_MINUTOS} minutos...")

            # Pausa
            time.sleep(wait_seconds)


if __name__ == "__main__":
    try:
        print("--- ZARA STOCK TRACKER INICIADO ---")
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("--- ZARA STOCK TRACKER DETENIDO MANUALMENTE ---")