#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para enviar un email REAL usando Brevo
¡ATENCIÓN! Este script enviará un email real a la dirección especificada
"""

import os
from dotenv import load_dotenv
from sib_api_v3_sdk import TransactionalEmailsApi, ApiClient, Configuration
from sib_api_v3_sdk.models import SendSmtpEmail, SendSmtpEmailTo, SendSmtpEmailSender

# Cargar variables de entorno
load_dotenv()

def enviar_email_prueba_real():
    """Enviar un email REAL de prueba"""
    print("🚀 ENVIANDO EMAIL REAL DE PRUEBA CON BREVO")
    print("=" * 60)
    
    # Verificar configuración
    api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('BREVO_SENDER_EMAIL')
    sender_name = os.getenv('BREVO_SENDER_NAME')
    
    if not all([api_key, sender_email, sender_name]):
        print("❌ Configuración incompleta. Verifica tu archivo .env")
        return
    
    print(f"✅ API Key: {api_key[:20]}...")
    print(f"✅ Remitente: {sender_email}")
    print(f"✅ Nombre: {sender_name}")
    
    # Solicitar email de destino
    print("\n📧 INGRESA EL EMAIL DE DESTINO PARA LA PRUEBA:")
    print("(Este email recibirá el mensaje de prueba)")
    
    # Para pruebas, usaremos un email de ejemplo
    # En producción, deberías pedir al usuario que ingrese el email
    test_email = "test@example.com"  # Cambia esto por un email real
    
    print(f"📤 Enviando email de prueba a: {test_email}")
    print("⚠️  ADVERTENCIA: Este email se enviará REALMENTE")
    
    # Confirmar envío
    confirmacion = input("\n¿Continuar con el envío? (s/n): ").lower().strip()
    
    if confirmacion != 's':
        print("❌ Envío cancelado por el usuario")
        return
    
    try:
        # Configurar cliente de Brevo
        configuration = Configuration()
        configuration.api_key['api-key'] = api_key
        
        api_instance = TransactionalEmailsApi(ApiClient(configuration))
        
        # Crear email de prueba
        send_smtp_email = SendSmtpEmail(
            to=[SendSmtpEmailTo(email=test_email, name="Usuario de Prueba")],
            sender=SendSmtpEmailSender(email=sender_email, name=sender_name),
            subject="🎉 ¡Prueba Exitosa de Brevo! - Sistema de Préstamos",
            html_content=f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Prueba de Brevo</title>
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
                        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                        color: white;
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .content {{
                        padding: 30px 25px;
                    }}
                    .success-icon {{
                        font-size: 48px;
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .footer {{
                        background: #f8f9fa;
                        padding: 20px 25px;
                        text-align: center;
                        border-top: 1px solid #e9ecef;
                    }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="header">
                        <h1>🎉 ¡PRUEBA EXITOSA!</h1>
                        <p>Brevo está funcionando perfectamente</p>
                    </div>
                    
                    <div class="content">
                        <div class="success-icon">✅</div>
                        
                        <h2 style="color: #28a745; text-align: center;">
                            ¡Brevo está configurado y funcionando!
                        </h2>
                        
                        <p style="font-size: 16px; text-align: center;">
                            Este email confirma que la integración con <strong>Brevo</strong> 
                            está funcionando correctamente en tu sistema de préstamos.
                        </p>
                        
                        <div style="background: #e8f5e8; border: 1px solid #c3e6cb; border-radius: 10px; padding: 20px; margin: 20px 0;">
                            <h3 style="color: #155724; margin-top: 0;">✅ Configuración Verificada:</h3>
                            <ul style="color: #155724;">
                                <li>API Key de Brevo funcionando</li>
                                <li>Remitente configurado correctamente</li>
                                <li>Sistema de envío operativo</li>
                                <li>Plantillas HTML funcionando</li>
                            </ul>
                        </div>
                        
                        <p style="text-align: center; color: #6c757d;">
                            Ahora puedes usar el sistema para enviar:
                        </p>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0;">
                            <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 15px; text-align: center;">
                                <strong>📧 Recibos de Pago</strong><br>
                                <small>Confirmaciones automáticas</small>
                            </div>
                            <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 15px; text-align: center;">
                                <strong>⚠️ Notificaciones de Atraso</strong><br>
                                <small>Recordatorios automáticos</small>
                            </div>
                        </div>
                        
                        <p style="text-align: center; color: #28a745; font-weight: bold;">
                            🚀 Tu sistema está listo para usar Brevo
                        </p>
                    </div>
                    
                    <div class="footer">
                        <div style="margin-bottom: 15px;">
                            <strong>Wandy Soluciones y Préstamos</strong><br>
                            Soluciones financieras a tu alcance
                        </div>
                        
                        <div style="font-size: 14px; color: #6c757d;">
                            📞 Tel: +809 326-3633<br>
                            📧 Email: {sender_email}<br>
                            🌐 Web: www.wandysoluciones.com
                        </div>
                        
                        <div style="margin-top: 20px; font-size: 12px; color: #adb5bd;">
                            Email de prueba enviado desde el sistema de Wandy Soluciones y Préstamos.
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
        )
        
        print("📤 Enviando email...")
        
        # Enviar email
        result = api_instance.send_transac_email(send_smtp_email)
        
        print("\n" + "=" * 60)
        print("🎉 ¡EMAIL ENVIADO EXITOSAMENTE!")
        print("=" * 60)
        print(f"✅ Message ID: {result.message_id}")
        print(f"✅ Destinatario: {test_email}")
        print(f"✅ Remitente: {sender_email}")
        print(f"✅ Asunto: {send_smtp_email.subject}")
        print("\n📋 Próximos pasos:")
        print("   1. Revisa la bandeja de entrada de {test_email}")
        print("   2. Verifica que el email llegó correctamente")
        print("   3. Configura la base de datos MySQL")
        print("   4. Ejecuta la aplicación completa")
        print("   5. ¡Disfruta de tu sistema con Brevo!")
        
    except Exception as e:
        print(f"\n❌ Error al enviar email: {str(e)}")
        print("\n🔧 Posibles soluciones:")
        print("   1. Verifica que tu API Key sea correcta")
        print("   2. Asegúrate de que el email remitente esté verificado en Brevo")
        print("   3. Revisa la conexión a internet")
        print("   4. Verifica que no hayas excedido el límite de emails")

if __name__ == "__main__":
    print("⚠️  ADVERTENCIA: Este script enviará un email REAL")
    print("Asegúrate de tener configurado tu archivo .env correctamente")
    print()
    
    enviar_email_prueba_real()
