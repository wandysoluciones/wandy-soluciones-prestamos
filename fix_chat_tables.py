#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar y recrear las tablas del chat
"""

from app import app, db

def fix_chat_tables():
    """Verifica y recrea las tablas del chat"""
    with app.app_context():
        try:
            # Primero, eliminar las tablas existentes si existen
            print("🗑️  Eliminando tablas existentes del chat...")
            from sqlalchemy import text
            db.session.execute(text('DROP TABLE IF EXISTS mensaje'))
            db.session.execute(text('DROP TABLE IF EXISTS conversacion'))
            db.session.commit()
            print("✅ Tablas eliminadas")
            
            # Crear todas las tablas desde cero
            print("🔨 Creando tablas del chat...")
            db.create_all()
            print("✅ Tablas creadas exitosamente")
            
            # Verificar que las tablas se crearon correctamente
            print("🔍 Verificando estructura de las tablas...")
            
            # Verificar tabla conversacion
            result = db.session.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'conversacion' 
                ORDER BY ORDINAL_POSITION
            """))
            
            print("\n📋 Estructura de la tabla 'conversacion':")
            for row in result:
                print(f"   - {row[0]}: {row[1]} {'(NULL)' if row[2] == 'YES' else '(NOT NULL)'} {f'DEFAULT {row[3]}' if row[3] else ''}")
            
            # Verificar tabla mensaje
            result = db.session.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'mensaje' 
                ORDER BY ORDINAL_POSITION
            """))
            
            print("\n📋 Estructura de la tabla 'mensaje':")
            for row in result:
                print(f"   - {row[0]}: {row[1]} {'(NULL)' if row[2] == 'YES' else '(NOT NULL)'} {f'DEFAULT {row[3]}' if row[3] else ''}")
            
            # Probar una consulta simple
            print("\n🧪 Probando consultas...")
            from app import Conversacion, Mensaje
            
            conversaciones = Conversacion.query.limit(1).all()
            mensajes = Mensaje.query.limit(1).all()
            
            print("✅ Consultas de prueba exitosas")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Reparando tablas del chat...")
    
    if fix_chat_tables():
        print("\n🎉 ¡Chat reparado correctamente!")
        print("   Ahora puedes acceder a /chat en tu aplicación")
    else:
        print("\n💥 Error al reparar el chat")
