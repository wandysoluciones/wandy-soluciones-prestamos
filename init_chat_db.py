#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para inicializar las tablas del chat en la base de datos
"""

import os
import sys
from dotenv import load_dotenv

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def init_chat_tables():
    """Inicializa las tablas del chat"""
    with app.app_context():
        try:
            # Crear todas las tablas
            db.create_all()
            print("✅ Tablas del chat creadas exitosamente")
            
            # Verificar que las tablas existen
            from app import Conversacion, Mensaje
            
            # Intentar hacer una consulta simple para verificar
            conversaciones = Conversacion.query.limit(1).all()
            mensajes = Mensaje.query.limit(1).all()
            
            print("✅ Tablas verificadas correctamente")
            print(f"   - Tabla 'conversacion': OK")
            print(f"   - Tabla 'mensaje': OK")
            
        except Exception as e:
            print(f"❌ Error al crear las tablas: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Inicializando tablas del chat...")
    load_dotenv()
    
    if init_chat_tables():
        print("\n🎉 ¡Chat inicializado correctamente!")
        print("   Ahora puedes acceder a /chat en tu aplicación")
    else:
        print("\n💥 Error al inicializar el chat")
        sys.exit(1)
