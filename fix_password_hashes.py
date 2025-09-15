#!/usr/bin/env python3
"""
Script para corregir contraseñas mal hasheadas en la base de datos
"""

import sys
import os
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://root:Wandi829.@localhost/wandy_soluciones')

def fix_password_hashes():
    """Corrige las contraseñas que no están hasheadas correctamente"""
    try:
        # Crear conexión a la base de datos
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Obtener todos los usuarios
            result = conn.execute(text("SELECT id, username, password_hash FROM usuario"))
            usuarios = result.fetchall()
            
            print(f"Encontrados {len(usuarios)} usuarios en la base de datos")
            
            usuarios_corregidos = 0
            
            for usuario in usuarios:
                user_id, username, password_hash = usuario
                
                # Verificar si el hash es válido
                try:
                    # Intentar verificar con una contraseña de prueba
                    check_password_hash(password_hash, "test_password")
                    print(f"Usuario {username}: Hash valido")
                    
                except (ValueError, TypeError) as e:
                    print(f"Usuario {username}: Hash invalido - {str(e)}")
                    
                    # Determinar contraseña por defecto basada en el username
                    if username == 'admin':
                        new_password = 'admin123'
                    else:
                        new_password = '123456'  # Contraseña temporal
                    
                    # Generar nuevo hash
                    new_hash = generate_password_hash(new_password)
                    
                    # Actualizar en la base de datos
                    conn.execute(
                        text("UPDATE usuario SET password_hash = :hash WHERE id = :id"),
                        {"hash": new_hash, "id": user_id}
                    )
                    
                    print(f"  -> Contrasena actualizada a: {new_password}")
                    usuarios_corregidos += 1
            
            # Confirmar cambios
            conn.commit()
            
            print(f"\nProceso completado:")
            print(f"   - Usuarios corregidos: {usuarios_corregidos}")
            print(f"   - Total usuarios: {len(usuarios)}")
            
            if usuarios_corregidos > 0:
                print("\nIMPORTANTE:")
                print("   Los usuarios con contrasenas corregidas deben cambiar su contrasena")
                print("   Contrasenas temporales asignadas:")
                print("   - admin: admin123")
                print("   - otros usuarios: 123456")
                
    except Exception as e:
        print(f"Error al conectar con la base de datos: {str(e)}")
        print("\nVerifica que:")
        print("1. MySQL esté ejecutándose")
        print("2. La base de datos 'wandy_soluciones' exista")
        print("3. Las credenciales en .env sean correctas")
        return False
    
    return True

if __name__ == "__main__":
    print("Iniciando correccion de contrasenas...")
    print("=" * 50)
    
    success = fix_password_hashes()
    
    if success:
        print("\nCorreccion completada exitosamente!")
    else:
        print("\nError durante la correccion")
        sys.exit(1)
