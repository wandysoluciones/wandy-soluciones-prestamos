# Sistema de Gestión de Préstamos - Wandy Soluciones

## Descripción
Sistema completo de gestión de préstamos con funcionalidades avanzadas para administradores y empleados, incluyendo generación de PDFs, gestión de usuarios con roles, y control de acceso basado en permisos.

## Características Principales

### 🔐 Gestión de Usuarios y Seguridad
- Sistema de login/logout seguro
- Roles de usuario (Administrador/Empleado)
- Control de acceso basado en permisos
- Gestión completa de usuarios (CRUD)
- Cambio de contraseñas y perfiles

### 👥 Gestión de Clientes
- Registro completo de clientes
- Información personal, laboral y de contacto
- Historial de préstamos
- Búsqueda y filtros avanzados
- Exportación a PDF

### 💰 Gestión de Préstamos
- Creación de préstamos con diferentes frecuencias
- Cálculo automático de cuotas
- Gestión de garantías
- Estados de préstamo (Activo, Pausado, Cancelado, Finalizado)
- Exportación de contratos a PDF

### 📊 Sistema de Pagos
- Registro de pagos por cuota
- Pagos extraordinarios y abonos al capital
- Diferentes tipos de pago
- Generación de recibos en PDF
- Control de cuotas atrasadas

### 💼 Contabilidad
- Control de capital disponible
- Registro de ingresos y gastos
- Balance contable en tiempo real
- Reportes financieros
- Exportación de balances a PDF

### 📈 Reportes y Estadísticas
- Dashboard con métricas en tiempo real
- Reportes de clientes, préstamos y pagos
- Reportes de atrasos y mora
- Exportación en múltiples formatos (PDF)
- Filtros por fechas y criterios

### 🖨️ Generación de Documentos
- Contratos de préstamo en PDF
- Recibos de pago en PDF
- Reportes detallados en PDF
- Listas de clientes, préstamos y pagos
- Descarga directa de documentos

## Requisitos del Sistema

### Software
- Python 3.8 o superior
- MySQL 5.7 o superior
- Navegador web moderno

### Dependencias de Python
- Flask 2.3.3
- Flask-SQLAlchemy 3.0.5
- Flask-Login 0.6.3
- ReportLab 4.0.4 (para PDFs)
- PyMySQL 1.1.0
- python-dotenv 1.0.0

## Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd sistema-prestamos
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar base de datos
- Crear base de datos MySQL llamada `wandy_soluciones`
- Configurar credenciales en archivo `.env`

### 5. Crear archivo .env
```env
SECRET_KEY=tu_clave_secreta_muy_segura
DATABASE_URL=mysql+pymysql://usuario:password@localhost/wandy_soluciones
```

### 6. Ejecutar la aplicación
```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Configuración Inicial

### Usuario Administrador por Defecto
- **Username:** admin
- **Password:** admin123
- **Rol:** Administrador

**⚠️ IMPORTANTE:** Cambiar la contraseña del administrador después del primer login.

## Uso del Sistema

### Roles de Usuario

#### Administrador
- Acceso completo a todas las funcionalidades
- Gestión de usuarios (crear, editar, eliminar)
- Eliminación de registros (clientes, préstamos, pagos, gastos)
- Generación de todos los reportes
- Control total del sistema

#### Empleado
- Acceso a funcionalidades básicas
- Crear y editar clientes y préstamos
- Registrar pagos
- Ver reportes básicos
- **NO puede eliminar registros**

### Funcionalidades Principales

#### Dashboard
- Vista general del sistema
- Estadísticas en tiempo real
- Acceso rápido a funciones principales

#### Gestión de Clientes
- Lista de clientes con búsqueda y filtros
- Formulario de registro completo
- Edición de información del cliente
- Vista detallada con historial de préstamos
- Exportación a PDF

#### Gestión de Préstamos
- Creación de préstamos con diferentes frecuencias
- Cálculo automático de cuotas
- Estados y seguimiento
- Gestión de garantías
- Exportación de contratos

#### Sistema de Pagos
- Registro de pagos por cuota
- Pagos extraordinarios
- Control de cuotas atrasadas
- Generación de recibos

#### Contabilidad
- Control de capital
- Registro de ingresos y gastos
- Balance contable
- Reportes financieros

#### Reportes
- Reportes por fechas
- Exportación en PDF
- Estadísticas detalladas
- Análisis de mora

## Estructura de Archivos

```
sistema-prestamos/
├── app.py                 # Aplicación principal Flask
├── requirements.txt       # Dependencias de Python
├── README.md             # Este archivo
├── .env                  # Variables de entorno (crear)
├── templates/            # Plantillas HTML
├── static/              # Archivos estáticos (CSS, JS, imágenes)
└── database/            # Scripts de base de datos
```

## Base de Datos

### Modelos Principales
- **Usuario:** Gestión de usuarios y roles
- **Cliente:** Información completa del cliente
- **Prestamo:** Datos del préstamo y garantías
- **Cuota:** Cuotas individuales del préstamo
- **Pago:** Registro de pagos realizados
- **Contabilidad:** Control de capital y transacciones
- **Gasto:** Registro de gastos e ingresos

## Seguridad

### Autenticación
- Sistema de login seguro
- Contraseñas hasheadas con Werkzeug
- Sesiones seguras con Flask-Login

### Autorización
- Control de acceso basado en roles
- Decoradores de seguridad
- Validación de permisos en cada función

### Validaciones
- Validación de datos de entrada
- Sanitización de formularios
- Control de acceso a funciones críticas

## Generación de PDFs

### Tecnología
- **ReportLab:** Biblioteca principal para generación de PDFs
- **Formato:** A4 con estilos profesionales
- **Contenido:** Tablas, texto formateado, colores

### Tipos de Documentos
- Contratos de préstamo
- Recibos de pago
- Reportes de clientes
- Reportes de préstamos
- Reportes de pagos
- Balance contable
- Listas generales

## Mantenimiento

### Backup de Base de Datos
- Realizar backups regulares de la base de datos
- Exportar datos críticos periódicamente
- Mantener copias de seguridad en ubicaciones seguras

### Logs y Monitoreo
- Revisar logs de la aplicación regularmente
- Monitorear el rendimiento del sistema
- Verificar la integridad de los datos

### Actualizaciones
- Mantener las dependencias actualizadas
- Revisar actualizaciones de seguridad
- Probar cambios en entorno de desarrollo

## Soporte y Contacto

### Problemas Comunes
1. **Error de conexión a base de datos:** Verificar credenciales y estado del servidor MySQL
2. **Error al generar PDFs:** Verificar instalación de ReportLab y dependencias
3. **Problemas de permisos:** Verificar configuración de roles de usuario

### Contacto
- **Desarrollador:** [Tu Nombre]
- **Email:** [tu-email@ejemplo.com]
- **Soporte:** [información de soporte]

## Licencia

Este proyecto está bajo la licencia [especificar licencia].

## Changelog

### Versión 1.0.0
- Sistema base de gestión de préstamos
- Gestión de usuarios con roles
- Generación de PDFs
- Sistema de contabilidad
- Reportes y estadísticas
- Control de acceso basado en permisos

---

**Desarrollado con ❤️ para Wandy Soluciones**
