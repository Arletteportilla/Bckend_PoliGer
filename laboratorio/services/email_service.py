"""
Servicio de email para el sistema PoliGer.
Maneja el envío de correos electrónicos del sistema.
"""
import os
import logging
from email.mime.image import MIMEImage
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

# Colores del sistema PoliGer
COLORS = {
    'primary': '#182D49',       # Azul oscuro (headerBackground)
    'primary_light': '#1E3A5F', # Azul un poco más claro
    'accent': '#E9AD14',        # Dorado (accent)
    'accent_hover': '#D49B0E',  # Dorado oscuro
    'text_dark': '#121212',     # Texto principal
    'text_light': '#FFFFFF',    # Texto sobre fondo oscuro
    'text_muted': '#6B7280',    # Texto secundario
    'bg_light': '#F3F4F6',      # Fondo claro
    'bg_card': '#FFFFFF',       # Fondo tarjeta
    'border': '#E5E7EB',        # Bordes
    'credentials_bg': '#EEF2F7',  # Fondo caja credenciales
    'credentials_border': '#C9D4E2',  # Borde caja credenciales
    'warning_bg': '#FEF9E7',    # Fondo advertencia
    'warning_border': '#E9AD14',  # Borde advertencia (dorado)
    'warning_text': '#92600A',  # Texto advertencia
}

# Ruta al logo
LOGO_PATH = os.path.join(
    settings.BASE_DIR, '..', 'PoliGer', 'assets', 'images', 'Ecuagenera.png'
)
# Ruta alternativa si la primera no existe
LOGO_PATH_ALT = os.path.join(settings.BASE_DIR, 'laboratorio', 'static', 'logo.png')


class EmailService:
    """Servicio para envío de correos electrónicos del sistema."""

    @staticmethod
    def _get_logo_path():
        """Obtiene la ruta al logo del sistema."""
        if os.path.exists(LOGO_PATH):
            return LOGO_PATH
        if os.path.exists(LOGO_PATH_ALT):
            return LOGO_PATH_ALT
        return None

    @staticmethod
    def enviar_email_bienvenida(user, password: str, rol_display: str) -> bool:
        """
        Envía email de bienvenida al nuevo usuario con sus credenciales.

        Args:
            user: Instancia del usuario creado
            password: Contraseña en texto plano
            rol_display: Nombre legible del rol asignado

        Returns:
            bool: True si el email se envió correctamente, False si falló
        """
        if not user.email:
            logger.warning(
                f"No se puede enviar email de bienvenida: "
                f"usuario {user.username} no tiene email"
            )
            return False

        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            logger.warning(
                "No se puede enviar email: EMAIL_HOST_USER o "
                "EMAIL_HOST_PASSWORD no están configurados en .env"
            )
            return False

        try:
            app_name = getattr(settings, 'APP_NAME', 'PoliGer - EcuaGenera')
            subject = f"Bienvenido a {app_name} - Tus credenciales de acceso"

            text_content = (
                f"Hola {user.first_name} {user.last_name},\n\n"
                f"Tu cuenta ha sido creada exitosamente en {app_name}.\n\n"
                f"Tus credenciales de acceso:\n"
                f"  Usuario: {user.username}\n"
                f"  Contraseña: {password}\n"
                f"  Rol asignado: {rol_display}\n\n"
                f"Accede al sistema en: {getattr(settings, 'APP_URL', '')}\n\n"
                f"IMPORTANTE: Por seguridad, te recomendamos cambiar tu "
                f"contraseña después de tu primer inicio de sesión.\n\n"
                f"Saludos,\n"
                f"El equipo de {app_name}"
            )

            html_content = EmailService._generar_html_bienvenida(
                user=user,
                password=password,
                rol_display=rol_display,
            )

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.mixed_subtype = 'related'

            # Adjuntar logo como imagen embebida (CID)
            logo_path = EmailService._get_logo_path()
            if logo_path:
                try:
                    with open(logo_path, 'rb') as f:
                        logo_data = f.read()
                    logo_image = MIMEImage(logo_data)
                    logo_image.add_header('Content-ID', '<logo_ecuagenera>')
                    logo_image.add_header('Content-Disposition', 'inline', filename='Ecuagenera.png')
                    msg.attach(logo_image)
                except Exception as logo_error:
                    logger.warning(f"No se pudo adjuntar el logo: {logo_error}")

            msg.send(fail_silently=False)

            logger.info(
                f"Email de bienvenida enviado exitosamente a "
                f"{user.email} (usuario: {user.username})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error enviando email de bienvenida a {user.email} "
                f"(usuario: {user.username}): {e}"
            )
            return False

    @staticmethod
    def _generar_html_bienvenida(user, password: str, rol_display: str) -> str:
        """Genera el HTML profesional para el email de bienvenida."""
        app_url = getattr(settings, 'APP_URL', 'http://207.180.230.88')
        app_name = getattr(settings, 'APP_NAME', 'PoliGer - EcuaGenera')
        c = COLORS

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: {c['bg_light']};">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: {c['bg_light']};">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="margin: 0 auto; background-color: {c['bg_card']}; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);">

                    <!-- Header con logo -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {c['primary']}, {c['primary_light']}); padding: 30px 40px; text-align: center;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 16px;">
                                        <img src="cid:logo_ecuagenera" alt="Ecuagenera" width="90" height="90" style="border-radius: 50%; border: 3px solid {c['accent']}; background-color: #ffffff;" />
                                    </td>
                                </tr>
                                <tr>
                                    <td style="text-align: center;">
                                        <h1 style="color: {c['text_light']}; margin: 0 0 4px 0; font-size: 24px; font-weight: 800; letter-spacing: 0.5px;">
                                            {app_name}
                                        </h1>
                                        <p style="color: {c['accent']}; margin: 0; font-size: 13px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase;">
                                            Sistema de Gesti&oacute;n de Laboratorio
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Barra dorada decorativa -->
                    <tr>
                        <td style="background-color: {c['accent']}; height: 4px; font-size: 0; line-height: 0;">&nbsp;</td>
                    </tr>

                    <!-- Mensaje de bienvenida -->
                    <tr>
                        <td style="padding: 36px 40px 16px 40px;">
                            <h2 style="color: {c['primary']}; margin: 0 0 14px 0; font-size: 22px; font-weight: 700;">
                                &iexcl;Bienvenido/a, {user.first_name}!
                            </h2>
                            <p style="color: {c['text_muted']}; margin: 0 0 20px 0; font-size: 15px; line-height: 1.7;">
                                Tu cuenta ha sido creada exitosamente en el sistema
                                <strong style="color: {c['primary']};">{app_name}</strong>.
                                A continuaci&oacute;n encontrar&aacute;s tus credenciales de acceso.
                            </p>
                        </td>
                    </tr>

                    <!-- Caja de credenciales -->
                    <tr>
                        <td style="padding: 0 40px 28px 40px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: {c['credentials_bg']}; border-radius: 10px; border: 1px solid {c['credentials_border']};">
                                <tr>
                                    <td style="padding: 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="padding-bottom: 16px; border-bottom: 1px solid {c['credentials_border']};">
                                                    <h3 style="color: {c['primary']}; margin: 0; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                                                        &#128274; Credenciales de Acceso
                                                    </h3>
                                                </td>
                                            </tr>
                                        </table>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-top: 16px;">
                                            <tr>
                                                <td style="padding: 10px 0; color: {c['text_muted']}; font-size: 13px; font-weight: 600; width: 130px; text-transform: uppercase; letter-spacing: 0.3px;">
                                                    Usuario
                                                </td>
                                                <td style="padding: 10px 0; color: {c['primary']}; font-size: 16px; font-weight: 700; font-family: 'Courier New', monospace;">
                                                    {user.username}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td colspan="2" style="border-bottom: 1px dashed {c['credentials_border']}; font-size: 0; height: 1px;">&nbsp;</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 10px 0; color: {c['text_muted']}; font-size: 13px; font-weight: 600; width: 130px; text-transform: uppercase; letter-spacing: 0.3px;">
                                                    Contrase&ntilde;a
                                                </td>
                                                <td style="padding: 10px 0; color: {c['primary']}; font-size: 16px; font-weight: 700; font-family: 'Courier New', monospace;">
                                                    {password}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td colspan="2" style="border-bottom: 1px dashed {c['credentials_border']}; font-size: 0; height: 1px;">&nbsp;</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 10px 0; color: {c['text_muted']}; font-size: 13px; font-weight: 600; width: 130px; text-transform: uppercase; letter-spacing: 0.3px;">
                                                    Rol asignado
                                                </td>
                                                <td style="padding: 10px 0;">
                                                    <span style="display: inline-block; background-color: {c['accent']}; color: {c['text_light']}; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 700;">
                                                        {rol_display}
                                                    </span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Bot&oacute;n Iniciar Sesi&oacute;n -->
                    <tr>
                        <td style="padding: 0 40px 28px 40px; text-align: center;">
                            <a href="{app_url}"
                               style="display: inline-block; background-color: {c['accent']}; color: {c['text_light']}; text-decoration: none; padding: 15px 50px; border-radius: 8px; font-size: 16px; font-weight: 700; letter-spacing: 0.5px; box-shadow: 0 3px 10px rgba(233, 173, 20, 0.35);">
                                Iniciar Sesi&oacute;n
                            </a>
                            <p style="color: {c['text_muted']}; margin: 12px 0 0 0; font-size: 12px;">
                                {app_url}
                            </p>
                        </td>
                    </tr>

                    <!-- Advertencia de seguridad -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: {c['warning_bg']}; border-radius: 8px; border-left: 4px solid {c['warning_border']};">
                                <tr>
                                    <td style="padding: 16px 20px;">
                                        <p style="color: {c['accent_hover']}; margin: 0 0 4px 0; font-size: 14px; font-weight: 700;">
                                            &#9888;&#65039; Recomendaci&oacute;n de Seguridad
                                        </p>
                                        <p style="color: {c['warning_text']}; margin: 0; font-size: 13px; line-height: 1.6;">
                                            Por seguridad, te recomendamos cambiar tu contrase&ntilde;a
                                            despu&eacute;s de tu primer inicio de sesi&oacute;n. No compartas
                                            tus credenciales con terceros.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: {c['primary']}; padding: 24px 40px; text-align: center;">
                            <p style="color: {c['accent']}; margin: 0 0 4px 0; font-size: 13px; font-weight: 600;">
                                {app_name}
                            </p>
                            <p style="color: rgba(255,255,255,0.5); margin: 0 0 2px 0; font-size: 11px;">
                                Orqu&iacute;deas del Ecuador
                            </p>
                            <p style="color: rgba(255,255,255,0.35); margin: 8px 0 0 0; font-size: 11px;">
                                Este es un correo autom&aacute;tico. No responder a este mensaje.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


email_service = EmailService()
