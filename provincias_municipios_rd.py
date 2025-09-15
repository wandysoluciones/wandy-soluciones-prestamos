# Provincias y Municipios de República Dominicana
# Datos actualizados según la división administrativa oficial

PROVINCIAS_MUNICIPIOS = {
    "Azua": [
        "Azua de Compostela", "Estebanía", "Guayabal", "Las Charcas", "Las Yayas de Viajama",
        "Padre Las Casas", "Peralta", "Pueblo Viejo", "Sabana Yegua", "Tábara Arriba"
    ],
    "Baoruco": [
        "Galván", "Los Ríos", "Neiba", "Tamayo", "Villa Jaragua"
    ],
    "Barahona": [
        "Barahona", "Cabral", "El Peñón", "Enriquillo", "Fundación", "Jaquimeyes", "La Ciénaga", "Las Salinas", "Paraíso", "Polo", "Vicente Noble"
    ],
    "Dajabón": [
        "Dajabón", "El Pino", "Loma de Cabrera", "Partido", "Restauración"
    ],
    "Distrito Nacional": [
        "Distrito Nacional"
    ],
    "Duarte": [
        "Arenoso", "Castillo", "Eugenio María de Hostos", "Las Guáranas", "Pimentel", "San Francisco de Macorís", "Villa Riva"
    ],
    "Elías Piña": [
        "Bánica", "Comendador", "El Llano", "Hondo Valle", "Juan Santiago", "Pedro Santana"
    ],
    "El Seibo": [
        "El Seibo", "Miches"
    ],
    "Espaillat": [
        "Cayetano Germosén", "Gaspar Hernández", "Jamao al Norte", "Moca", "San Víctor"
    ],
    "Hato Mayor": [
        "El Valle", "Hato Mayor del Rey", "Sabana de la Mar"
    ],
    "Hermanas Mirabal": [
        "Salcedo", "Tenares", "Villa Tapia"
    ],
    "Independencia": [
        "Cristóbal", "Duvergé", "Jimaní", "La Descubierta", "Mella", "Postrer Río"
    ],
    "La Altagracia": [
        "Higüey", "San Rafael del Yuma"
    ],
    "La Romana": [
        "Guaymate", "La Romana", "Villa Hermosa"
    ],
    "La Vega": [
        "Constanza", "Jarabacoa", "Jima Abajo", "La Vega", "Río Verde Arriba", "Tireo"
    ],
    "María Trinidad Sánchez": [
        "Cabrera", "El Factor", "Nagua", "Río San Juan"
    ],
    "Monseñor Nouel": [
        "Bonao", "Maimón", "Piedra Blanca"
    ],
    "Monte Cristi": [
        "Castañuela", "Guayubín", "Las Matas de Santa Cruz", "Monte Cristi", "Pepillo Salcedo", "San Fernando de Monte Cristi", "Villa Vásquez"
    ],
    "Monte Plata": [
        "Bayaguana", "Monte Plata", "Peralvillo", "Sabana Grande de Boyá", "Yamasá"
    ],
    "Pedernales": [
        "Oviedo", "Pedernales"
    ],
    "Peravia": [
        "Baní", "Nizao", "Paya"
    ],
    "Puerto Plata": [
        "Altamira", "Guananico", "Imbert", "Los Hidalgos", "Luperón", "Puerto Plata", "Sosúa", "Villa Isabela", "Villa Montellano"
    ],
    "Samaná": [
        "Las Terrenas", "Samaná", "Sánchez"
    ],
    "San Cristóbal": [
        "Bajos de Haina", "Cambita Garabitos", "Los Cacaos", "Sabana Grande de Palenque", "San Cristóbal", "San Gregorio de Nigua", "Villa Altagracia", "Yaguate"
    ],
    "San José de Ocoa": [
        "Rancho Arriba", "Sabana Larga", "San José de Ocoa"
    ],
    "San Juan": [
        "Bohechío", "El Cercado", "Juan de Herrera", "Las Matas de Farfán", "San Juan de la Maguana", "Vallejuelo"
    ],
    "San Pedro de Macorís": [
        "Consuelo", "Guayacanes", "Quisqueya", "Ramón Santana", "San José de los Llanos", "San Pedro de Macorís"
    ],
    "Sánchez Ramírez": [
        "Cevicos", "Cotui", "Fantino", "La Mata"
    ],
    "Santiago": [
        "Bisonó", "Jánico", "Licey al Medio", "Puñal", "Sabana Iglesia", "San José de las Matas", "Santiago de los Caballeros", "Tamboril", "Villa Bisonó", "Villa González"
    ],
    "Santiago Rodríguez": [
        "Monción", "San Ignacio de Sabaneta", "Villa Los Almácigos"
    ],
    "Santo Domingo": [
        "Boca Chica", "Los Alcarrizos", "Pedro Brand", "San Antonio de Guerra", "San Luis", "Santo Domingo Este", "Santo Domingo Norte", "Santo Domingo Oeste"
    ],
    "Valverde": [
        "Esperanza", "Laguna Salada", "Mao"
    ]
}

# Función para obtener municipios de una provincia
def obtener_municipios(provincia):
    """Retorna la lista de municipios de una provincia específica"""
    return PROVINCIAS_MUNICIPIOS.get(provincia, [])

# Función para obtener todas las provincias
def obtener_provincias():
    """Retorna la lista de todas las provincias"""
    return list(PROVINCIAS_MUNICIPIOS.keys())

# Función para obtener todas las provincias y municipios
def obtener_todas_provincias_municipios():
    """Retorna el diccionario completo de provincias y municipios"""
    return PROVINCIAS_MUNICIPIOS.copy()

# Función para validar provincia y municipio
def validar_provincia_municipio(provincia, municipio):
    """Valida si una provincia y municipio son válidos"""
    if provincia not in PROVINCIAS_MUNICIPIOS:
        return False
    return municipio in PROVINCIAS_MUNICIPIOS[provincia]

if __name__ == "__main__":
    # Ejemplo de uso
    print("Provincias de República Dominicana:")
    for provincia in obtener_provincias():
        print(f"- {provincia}")
    
    print("\nMunicipios de Santo Domingo:")
    municipios_sd = obtener_municipios("Santo Domingo")
    for municipio in municipios_sd:
        print(f"  - {municipio}")
