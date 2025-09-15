"""
CONFIGURACIÓN Y FUNCIONES PARA BREVO (SENDINBLUE)
Sistema de envío de emails para Wandy Soluciones y Préstamos
"""

import os
from dotenv import load_dotenv
from sib_api_v3_sdk import TransactionalEmailsApi, ApiClient, Configuration
from sib_api_v3_sdk.models.send_smtp_email import SendSmtpEmail
from sib_api_v3_sdk.models.send_smtp_email_to import SendSmtpEmailTo
from sib_api_v3_sdk.models.send_smtp_email_sender import SendSmtpEmailSender
from sib_api_v3_sdk.models.send_smtp_email_reply_to import SendSmtpEmailReplyTo
import logging

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrevoEmailService:
    """Servicio de envío de emails usando Brevo"""
    
    def __init__(self):
        """Inicializar servicio de Brevo"""
        self.api_key = os.getenv('BREVO_API_KEY')
        self.sender_email = os.getenv('BREVO_SENDER_EMAIL', 'info@wandysoluciones.com')
        self.sender_name = os.getenv('BREVO_SENDER_NAME', 'Wandy Soluciones y Préstamos')
        self.reply_to = os.getenv('BREVO_REPLY_TO', 'info@wandysoluciones.com')
        
        if not self.api_key:
            raise ValueError("BREVO_API_KEY no está configurada en las variables de entorno")
        
        # Configurar cliente de Brevo
        self.config = Configuration()
        self.config.api_key['api-key'] = self.api_key
        self.api_client = ApiClient(self.config)
        self.email_api = TransactionalEmailsApi(self.api_client)
        
        logger.info("✅ Servicio de Brevo inicializado correctamente")
    
    def enviar_recibo_pago(self, cliente_email, cliente_nombre, datos_pago):
        """
        Enviar recibo de pago por email
        
        Args:
            cliente_email (str): Email del cliente
            cliente_nombre (str): Nombre completo del cliente
            datos_pago (dict): Datos del pago
            
        Returns:
            dict: Resultado del envío
        """
        try:
            # Preparar datos del email
            subject = f"Recibo de Pago #{datos_pago['pago_id']} - {cliente_nombre}"
            
            # Crear contenido HTML del recibo
            html_content = self._generar_html_recibo_pago(cliente_nombre, datos_pago)
            
            # Configurar email
            send_email = SendSmtpEmail(
                to=[SendSmtpEmailTo(email=cliente_email, name=cliente_nombre)],
                sender=SendSmtpEmailSender(email=self.sender_email, name=self.sender_name),
                reply_to=SendSmtpEmailReplyTo(email=self.reply_to),
                subject=subject,
                html_content=html_content
            )
            
            # Enviar email
            result = self.email_api.send_transac_email(send_email)
            
            logger.info(f"✅ Recibo de pago enviado exitosamente a {cliente_email}")
            return {
                'success': True,
                'message_id': result.message_id,
                'message': 'Email enviado exitosamente'
            }
            
        except Exception as e:
            logger.error(f"❌ Error al enviar recibo de pago: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Error al enviar email'
            }
    
    def enviar_notificacion_atraso(self, cliente_email, cliente_nombre, datos_cuota):
        """
        Enviar notificación de cuota atrasada
        
        Args:
            cliente_email (str): Email del cliente
            cliente_nombre (str): Nombre completo del cliente
            datos_cuota (dict): Datos de la cuota atrasada
            
        Returns:
            dict: Resultado del envío
        """
        try:
            # Preparar datos del email
            subject = f"Recordatorio de Pago Atrasado - {cliente_nombre}"
            
            # Crear contenido HTML de la notificación
            html_content = self._generar_html_notificacion_atraso(cliente_nombre, datos_cuota)
            
            # Configurar email
            send_email = SendSmtpEmail(
                to=[SendSmtpEmailTo(email=cliente_email, name=cliente_nombre)],
                sender=SendSmtpEmailSender(email=self.sender_email, name=self.sender_name),
                reply_to=SendSmtpEmailReplyTo(email=self.reply_to),
                subject=subject,
                html_content=html_content
            )
            
            # Enviar email
            result = self.email_api.send_transac_email(send_email)
            
            logger.info(f"✅ Notificación de atraso enviada exitosamente a {cliente_email}")
            return {
                'success': True,
                'message_id': result.message_id,
                'message': 'Notificación enviada exitosamente'
            }
            
        except Exception as e:
            logger.error(f"❌ Error al enviar notificación de atraso: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Error al enviar notificación'
            }
    
    def _generar_html_recibo_pago(self, cliente_nombre, datos_pago):
        """Generar HTML para recibo de pago"""
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Recibo de Pago - {datos_pago['pago_id']}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .email-container {{
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                .company-name {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .company-slogan {{
                    font-size: 14px;
                    opacity: 0.9;
                }}
                .content {{
                    padding: 30px 25px;
                }}
                .section-title {{
                    color: #667eea;
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #e9ecef;
                    padding-bottom: 10px;
                }}
                .info-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 15px;
                    align-items: center;
                }}
                .info-label {{
                    font-weight: 600;
                    color: #495057;
                }}
                .info-value {{
                    font-weight: 500;
                    color: #212529;
                }}
                .amount-highlight {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #28a745;
                }}
                .separator {{
                    border-top: 2px dotted #dee2e6;
                    margin: 25px 0;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px 25px;
                    text-align: center;
                    border-top: 1px solid #e9ecef;
                }}
                .contact-info {{
                    font-size: 14px;
                    color: #6c757d;
                    margin-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <div class="company-name">WANDY SOLUCIONES Y PRÉSTAMOS</div>
                    <div class="company-slogan">Soluciones financieras a tu alcance</div>
                </div>
                
                <div class="content">
                    <div style="text-align: center; margin-bottom: 25px;">
                        <h2 style="color: #667eea;">Recibo de Pago #{datos_pago['pago_id']}</h2>
                        <p style="color: #6c757d;">Fecha de Emisión: {datos_pago['fecha_pago']}</p>
                    </div>
                    
                    <div class="section-title">Información del Cliente</div>
                    <div class="info-row">
                        <span class="info-label">Cliente:</span>
                        <span class="info-value">{cliente_nombre}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Préstamo:</span>
                        <span class="info-value">#{datos_pago['prestamo_id']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Cuota:</span>
                        <span class="info-value">#{datos_pago['cuota_numero']}</span>
                    </div>
                    
                    <div class="separator"></div>
                    
                    <div class="section-title">Detalles del Pago</div>
                    <div class="info-row">
                        <span class="info-label">Monto Total:</span>
                        <span class="info-value amount-highlight">RD${datos_pago['monto_total']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Capital:</span>
                        <span class="info-value">RD${datos_pago['monto_capital']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Intereses:</span>
                        <span class="info-value">RD${datos_pago['monto_interes']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Fecha de Pago:</span>
                        <span class="info-value">{datos_pago['fecha_pago']}</span>
                    </div>
                    
                    <div class="separator"></div>
                    
                    <p style="text-align: center; color: #28a745; font-weight: bold; font-size: 18px;">
                        ✅ Pago Confirmado
                    </p>
                    
                    <p style="text-align: center; color: #6c757d; font-size: 14px;">
                        Este es un recibo oficial de Wandy Soluciones y Préstamos.<br>
                        Por favor, guárdelo para sus registros.
                    </p>
                </div>
                
                <div class="footer">
                    <div class="contact-info">
                        <strong>Wandy Soluciones y Préstamos</strong><br>
                        Soluciones financieras a tu alcance
                    </div>
                    
                    <div class="contact-info">
                        📞 Tel: +809 326-3633<br>
                        📧 Email: info@wandysoluciones.com<br>
                        🌐 Web: www.wandysoluciones.com
                    </div>
                    
                    <div style="margin-top: 20px; font-size: 12px; color: #adb5bd;">
                        Este email fue enviado automáticamente desde el sistema de Wandy Soluciones y Préstamos.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generar_html_notificacion_atraso(self, cliente_nombre, datos_cuota):
        """Generar HTML para notificación de atraso"""
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Recordatorio de Pago Atrasado</title>
            <style>
                body {{
                    font-family: 'arial, helvetica, sans-serif';
                    line-height: 1.5;
                    color: #3b3f44;
                    font-size: 16px;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                
                .email-container {{
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                
                .company-name {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                
                .company-slogan {{
                    font-size: 14px;
                    opacity: 0.9;
                }}
                
                .content {{
                    padding: 30px 25px;
                }}
                
                .section-title {{
                    color: #1F2D3D;
                    font-family: 'arial, helvetica, sans-serif';
                    font-size: 18px;
                    font-weight: 400;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #e9ecef;
                    padding-bottom: 10px;
                }}
                
                .info-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 15px;
                    align-items: center;
                }}
                
                .info-label {{
                    font-weight: 600;
                    color: #495057;
                }}
                
                .info-value {{
                    font-weight: 500;
                    color: #212529;
                }}
                
                .amount-highlight {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #dc3545;
                }}
                
                .separator {{
                    border-top: 2px dotted #dee2e6;
                    margin: 25px 0;
                }}
                
                .alert {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                    border-left: 4px solid #f39c12;
                }}
                
                .help-box {{
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                
                .footer {{
                    background: #f8f9fa;
                    padding: 20px 25px;
                    text-align: center;
                    border-top: 1px solid #e9ecef;
                }}
                
                .contact-info {{
                    font-size: 14px;
                    color: #6c757d;
                    margin-bottom: 10px;
                }}
                
                .social-links {{
                    margin-top: 15px;
                }}
                
                .social-links a {{
                    color: #0092ff;
                    text-decoration: underline;
                    font-family: 'arial, helvetica, sans-serif';
                    font-size: 16px;
                    margin: 0 10px;
                }}
                
                .social-links a:hover {{
                    text-decoration: underline;
                }}
                
                .view-in-browser {{
                    text-align: center;
                    padding: 5px 30px;
                    margin-bottom: 10px;
                }}
                
                .view-in-browser a {{
                    color: #858588;
                    font-family: 'arial, helvetica, sans-serif';
                    font-size: 12px;
                    text-decoration: underline;
                }}
                
                .notification-title {{
                    text-align: center;
                    font-size: 20px;
                    color: #dc3545;
                    margin-bottom: 25px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="view-in-browser">
                    <p><a href="#">Ver en navegador</a></p>
                </div>
                <div class="header">
                    <img style="width: 150px; height: auto; display: block; margin: 0 auto 10px;" src="https://i.imgur.com/Ui2SzsR.jpg" alt="Logo de Wandy Soluciones y Préstamos">
                    <div class="company-name">WANDY SOLUCIONES Y PRÉSTAMOS</div>
                    <div class="company-slogan">Soluciones financieras a tu alcance</div>
                </div>
                
                <div class="content">
                    <div class="notification-title">
                        ⚠️ Recordatorio de Pago Atrasado
                    </div>
                    
                    <div class="alert">
                        <p style="margin: 0; font-size: 16px;">
                            <strong>Estimado/a {cliente_nombre},</strong><br><br>
                            Le recordamos que tiene una cuota atrasada que requiere su atención inmediata.
                        </p>
                    </div>
                    
                    <div class="section-title">Detalles de la Cuota Atrasada</div>
                    
                    <div class="info-row">
                        <span class="info-label">Monto del Préstamo:</span>
                        <span class="info-value">RD${datos_cuota.get('monto_prestamo', '0.00')}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Cuota:</span>
                        <span class="info-value">{datos_cuota.get('cuota_numero', 'N/A')}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Fecha de Vencimiento:</span>
                        <span class="info-value">{datos_cuota.get('fecha_vencimiento', 'N/A')}</span>
                    </div>
                    
                    <div class="separator"></div>
                    
                    <div class="section-title">Información Financiera</div>
                    
                    <div class="info-row">
                        <span class="info-label">Monto Original:</span>
                        <span class="info-value">RD${datos_cuota.get('monto_original', '0.00')}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Interés por Atraso:</span>
                        <span class="info-value amount-highlight">RD${datos_cuota.get('interes_atraso', '0.00')}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Monto Total a Pagar:</span>
                        <span class="info-value amount-highlight">RD${datos_cuota.get('monto_total', '0.00')}</span>
                    </div>
                    
                    <div class="separator"></div>
                    
                    <div class="help-box">
                        <h4 style="color: #155724; margin-top: 0;">📞 ¿Necesita Ayuda?</h4>
                        <p style="color: #155724; margin-bottom: 0;">
                            Si tiene alguna pregunta o necesita hacer un arreglo de pago, 
                            no dude en contactarnos. Estamos aquí para ayudarle.
                        </p>
                    </div>
                    
                    <p style="text-align: center; color: #6c757d; font-size: 14px;">
                        Por favor, regularice su pago lo antes posible para evitar cargos adicionales.
                    </p>
                </div>
                
                <div class="footer">
                    <div class="contact-info">
                        <strong>Wandy Soluciones y Préstamos</strong><br>
                        Soluciones financieras a tu alcance
                    </div>
                    
                    <div class="contact-info">
                        📞 Tel: +809 326-3633<br>
                        📧 Email: info@wandysoluciones.com<br>
                        🌐 Web: www.wandysoluciones.com
                    </div>
                    
                    <div class="social-links">
                        <a href="https://www.facebook.com/share/1B3zAZmT11/?mibextid=wwXIfr">Facebook</a> |
                        <a href="https://www.instagram.com/wandy_soluciones?igsh=MWM5Ynl2cG41eTc3aw%3D%3D&utm_source=">Instagram</a> |
                        <a href="https://wa.me/18093263633">WhatsApp</a>
                    </div>
                    
                    <div style="margin-top: 20px; font-size: 12px; color: #adb5bd;">
                        Este email fue enviado automáticamente desde el sistema de Wandy Soluciones y Préstamos.<br>
                        Si tiene alguna pregunta, por favor contáctenos directamente.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def verificar_conexion(self):
        """Verificar conexión con Brevo"""
        try:
            # Intentar obtener información de la cuenta
            account = self.email_api.get_account()
            logger.info(f"✅ Conexión con Brevo exitosa. Cuenta: {account.email}")
            return True
        except Exception as e:
            logger.error(f"❌ Error de conexión con Brevo: {str(e)}")
            return False

# Función de utilidad para crear instancia del servicio
def crear_servicio_brevo():
    """Crear instancia del servicio de Brevo"""
    try:
        return BrevoEmailService()
    except Exception as e:
        logger.error(f"❌ Error al crear servicio de Brevo: {str(e)}")
        return None

# Funciones de conveniencia para uso directo
def enviar_recibo_pago_brevo(cliente_email, cliente_nombre, datos_pago):
    """Función de conveniencia para enviar recibo de pago"""
    servicio = crear_servicio_brevo()
    if servicio:
        return servicio.enviar_recibo_pago(cliente_email, cliente_nombre, datos_pago)
    return {'success': False, 'error': 'Servicio no disponible'}

def enviar_notificacion_atraso_brevo(cliente_email, cliente_nombre, datos_cuota):
    """Función de conveniencia para enviar notificación de atraso"""
    servicio = crear_servicio_brevo()
    if servicio:
        return servicio.enviar_notificacion_atraso(cliente_email, cliente_nombre, datos_cuota)
    return {'success': False, 'error': 'Servicio no disponible'}
