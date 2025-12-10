import asyncio
from playwright.async_api import async_playwright, Error as PlaywrightError
import smtplib
from email.message import EmailMessage
import time

# ==============================================================================
#                      I. CONFIGURACIÓN DEL PRODUCTO Y RASTREO
# ==============================================================================
PRODUCT_URL = "https://www.zara.com/es/es/jersey-punto-lazo-p03920940.html?v1=484707602"
TALLA_BUSCADA = "xl"
# SELECTOR DE TALLA: Búsqueda simple por texto.
TALLA_SELECTOR = f'button:has-text("{TALLA_BUSCADA}")'

# SELECTOR DEL BOTÓN INICIAL ("Añadir")
BUTTON_OPEN_SELECTOR = "xpath=//button[contains(translate(normalize-space(.), 'AÑADIR', 'añadir'), 'añadir')]"

# SELECTOR DE COOKIES
COOKIES_SELECTOR = 'button:has-text("Aceptar")'

TIMEOUT_MS = 20000

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
    """Envía un correo electrónico con codificación UTF-8 para aceptar la 'ñ' y tildes."""
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

    except Exception as e:
        print(f"   -> ERROR al enviar el email: {e}")


async def check_zara_stock():
    """Función principal que navega, comprueba el stock y notifica."""
    print(f"[{TALLA_BUSCADA}] Iniciando comprobación de stock...")

    async with async_playwright() as p:
        # MODO DEPURACIÓN: Cambiar a 'headless=True' para el hosting.
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()

        try:
            # 1. Navegación e interacciones iniciales
            print("1. Navegando a la URL...")
            await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            await page.wait_for_timeout(2000)

            # 2. Cookies
            try:
                print("2. Intentando aceptar cookies...")
                await page.click(COOKIES_SELECTOR, timeout=5000)
                print("   (Cookies aceptadas con éxito).")
            except Exception:
                pass

            await page.wait_for_timeout(2000)

            # 3. Clicar en "Añadir"
            try:
                print(f"3. Intentando pulsar el botón inicial 'Añadir'...")
                await page.click(BUTTON_OPEN_SELECTOR, timeout=5000)
                print("   (Botón 'Añadir' pulsado con éxito).")
            except Exception as e:
                print(f"   🛑 ERROR: No se pudo pulsar el botón 'Añadir'. Error: {e}")

            await page.wait_for_timeout(2000)

            # 4. Esperar que la talla esté visible
            print(f"4. Esperando que la talla '{TALLA_BUSCADA}' esté visible (Máx {TIMEOUT_MS / 1000}s)...")

            talla_element = page.locator(TALLA_SELECTOR).first
            await talla_element.wait_for(state="visible", timeout=TIMEOUT_MS)

            # 5. VERIFICACIÓN DE DISPONIBILIDAD (INTENTAR CLIC)
            print("5. Verificando disponibilidad intentando hacer clic...")

            # Intentamos hacer clic. Si el botón está agotado/gris/cubierto, Playwright fallará aquí.
            # Aumentamos el timeout del clic por si acaso
            await talla_element.click(timeout=3000)

            # 6. ÉXITO (Si el código llega aquí, el clic fue exitoso -> ¡HAY STOCK!)
            resultado = f"🎉 STOCK ENCONTRADO: ¡La talla '{TALLA_BUSCADA}' parece estar disponible! Revisa la web YA: {PRODUCT_URL}"
            print(resultado)

            send_email(
                subject=f"[ALERTA ZARA] ¡Stock de talla {TALLA_BUSCADA} encontrado!",
                body=resultado
            )

        # Capturamos el error de Playwright (TimeoutError, ElementNotVisibleError, etc.)
        except PlaywrightError as e:
            # Si el clic falla por intercepción, deshabilitado o timeout, asumimos agotado
            resultado = f"❌ RESULTADO: La talla '{TALLA_BUSCADA}' sigue agotada (Clic bloqueado/Talla no seleccionable)."
            print(resultado)

        except Exception as e:
            # Capturamos cualquier otro error
            error_message = f"🛑 Ocurrió un error general: {e}"
            print(error_message)

        finally:
            await page.wait_for_timeout(5000)
            await browser.close()
            print("Comprobación finalizada.")


if __name__ == "__main__":
    asyncio.run(check_zara_stock())