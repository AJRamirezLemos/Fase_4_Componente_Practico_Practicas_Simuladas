"""
UNAD - Curso Programación 213023
Fase 4 - Ejercicio 1: Sistema Integral de Gestión de Clientes, Servicios
y Reservas

Empresa: Software FJ

Aplicación de consola desarrollada con programación orientada a objetos.
No utiliza bases de datos. Los datos se gestionan en listas en memoria y
los eventos/errores se registran en un archivo de texto (software_fj.log).

VERSIÓN 3 (mejorada a partir del código base de Javier y de las dos
retroalimentaciones del tutor).
Los cambios respecto a la versión original están marcados con la etiqueta
"NUEVO" y el número de la recomendación del tutor que atienden:

  [REC-1] Ruta del log compatible con .py y con cuaderno .ipynb.
  [REC-2] Validación de tipos (texto, None, bool, NaN, infinito) antes de
          validar rangos.
  [REC-3] Pruebas independientes: nombre, correo y teléfono por separado;
          creación incorrecta de servicios; servicio no disponible.
  [REC-4] Resultados visibles: salida en consola + extracto del log.
  [REC-5] Continuidad: cada operación está aislada; un error no detiene
          la demostración.
  [REC-6] Sobrecarga simulada integrada como método de la clase Servicio
          (calcular_costo_total) y distinguida de la sobrescritura.
  [CORR]  Corrección de sangría/estructura del código original
          (Entidad.__init__ y la propiedad id quedaban fuera de la clase).

Correcciones de la segunda retroalimentación del tutor:

  [REC-7] El parámetro principal de calcular_costo / calcular_costo_total
          se renombra a 'unidades' y es de solo posición. Así ya no choca
          con la opción 'cantidad' de AlquilerEquipo (TypeError).
  [REC-8] SistemaSoftwareFJ.crear_reserva() ya no compara solo
          identificadores: exige que cliente y servicio sean EXACTAMENTE los
          objetos registrados. Se agrega nueva_reserva(), que arma la reserva
          a partir de los objetos que guarda el gestor.
  [REC-9] Las pruebas verifican valores concretos (costos, estados,
          cantidad de objetos registrados) y no solo la ausencia de errores.
"""

from abc import ABC, abstractmethod
from datetime import datetime
import logging
import math          # NUEVO [REC-2]: para detectar NaN e infinito (math.isfinite)
import re            # NUEVO: expresión regular para validar el correo
import tempfile      # NUEVO [REC-1]: carpeta alternativa si no se puede escribir el log
from pathlib import Path

# =============================================================================
# 1. REGISTRO DE EVENTOS (LOG)
# =============================================================================


def obtener_ruta_log():
    """NUEVO [REC-1]: devuelve la ruta del archivo de log según el entorno.

    - En un archivo .py existe __file__, y el log queda junto al script.
    - En un cuaderno .ipynb (Jupyter/Colab) __file__ NO existe y lanza
      NameError; en ese caso se usa la carpeta de trabajo actual.
    """
    try:
        carpeta = Path(__file__).resolve().parent
    except NameError:
        carpeta = Path.cwd()
    return carpeta / "software_fj.log"


def configurar_logger():
    """NUEVO [REC-1]: crea el logger con su propio FileHandler.

    Se evita logging.basicConfig porque en un cuaderno el logger raíz ya
    tiene manejadores y basicConfig se ignora en silencio (el log quedaría
    vacío). Además se evita duplicar manejadores si la celda se ejecuta
    varias veces.
    """
    ruta = obtener_ruta_log()
    log = logging.getLogger("SoftwareFJ")
    log.setLevel(logging.INFO)
    log.propagate = False  # no mezclar con el logger raíz del cuaderno

    # Si ya hay un FileHandler (celda ejecutada de nuevo), se reutiliza.
    for h in log.handlers:
        if isinstance(h, logging.FileHandler):
            return log, Path(h.baseFilename)

    formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    try:
        manejador = logging.FileHandler(ruta, encoding="utf-8")
    except OSError:
        # Carpeta sin permiso de escritura: se usa la carpeta temporal.
        ruta = Path(tempfile.gettempdir()) / "software_fj.log"
        manejador = logging.FileHandler(ruta, encoding="utf-8")
    manejador.setFormatter(formato)
    log.addHandler(manejador)
    return log, ruta


logger, RUTA_LOG = configurar_logger()

# =============================================================================
# 2. EXCEPCIONES PROPIAS
# =============================================================================


class ErrorSistema(Exception):
    """Excepción base para los errores controlados de la aplicación."""


class DatosInvalidosError(ErrorSistema):
    """Se produce cuando un dato no cumple las reglas de validación."""


class ElementoNoEncontradoError(ErrorSistema):
    """Se produce cuando se solicita un cliente, servicio o reserva
    inexistente."""


class OperacionNoPermitidaError(ErrorSistema):
    """Se produce cuando el estado del objeto no permite una operación."""


class ServicioNoDisponibleError(ErrorSistema):
    """Se produce cuando un servicio no está habilitado."""


# =============================================================================
# 3. FUNCIONES AUXILIARES DE VALIDACIÓN  (NUEVO [REC-2])
# =============================================================================


def validar_numero(valor, nombre, *, entero=False, minimo=None, maximo=None,
                   estricto_minimo=False):
    """NUEVO [REC-2]: valida PRIMERO el tipo y DESPUÉS el rango.

    Orden de las comprobaciones (cada una lanza DatosInvalidosError):
      1. Que no sea bool (en Python True/False son int: True == 1 y se
         colaría como "1 hora").
      2. Que sea int o float (rechaza texto, None, listas, etc.).
      3. Que sea finito (rechaza NaN e infinito).
      4. Que sea entero, si se exige.
      5. Que esté dentro del rango (mínimo/máximo).
    Devuelve el mismo valor si todo está bien.
    """
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise DatosInvalidosError(
            f"{nombre}: se esperaba un valor numérico y se recibió "
            f"{type(valor).__name__} ({valor!r})."
        )
    if isinstance(valor, float) and not math.isfinite(valor):
        raise DatosInvalidosError(f"{nombre}: no puede ser NaN ni infinito.")
    if entero and not isinstance(valor, int):
        raise DatosInvalidosError(f"{nombre}: se esperaba un número entero.")
    if minimo is not None:
        if valor < minimo or (estricto_minimo and valor == minimo):
            simbolo = "mayor que" if estricto_minimo else "mayor o igual a"
            raise DatosInvalidosError(f"{nombre}: debe ser {simbolo} {minimo}.")
    if maximo is not None and valor > maximo:
        raise DatosInvalidosError(f"{nombre}: debe ser menor o igual a {maximo}.")
    return valor


def validar_texto(valor, nombre, minimo=1):
    """NUEVO [REC-2]: valida que sea str (no None, no números) con un
    mínimo de caracteres, y devuelve el texto sin espacios sobrantes."""
    if not isinstance(valor, str):
        raise DatosInvalidosError(
            f"{nombre}: se esperaba texto y se recibió {type(valor).__name__}."
        )
    limpio = valor.strip()
    if len(limpio) < minimo:
        raise DatosInvalidosError(
            f"{nombre}: debe tener al menos {minimo} caracter(es)."
        )
    return limpio


# =============================================================================
# 4. ENTIDAD ABSTRACTA
# =============================================================================


class Entidad(ABC):
    """Define la estructura común de las entidades del sistema."""

    # CORR: en el original, __init__, id y obtener_informacion estaban sin
    # sangría (fuera de la clase). Ahora están dentro de Entidad.
    def __init__(self, identificador):
        # NUEVO [REC-2]: el identificador puede ser texto o entero, pero
        # nunca bool/None/vacío.
        if isinstance(identificador, bool) or identificador is None:
            raise DatosInvalidosError("El identificador es obligatorio.")
        if not str(identificador).strip():
            raise DatosInvalidosError("El identificador es obligatorio.")
        self._id = str(identificador).strip()
        self._fecha_creacion = datetime.now()

    @property
    def id(self):
        return self._id

    @property
    def fecha_creacion(self):
        return self._fecha_creacion

    @abstractmethod
    def obtener_informacion(self):
        """Devuelve una descripción legible de la entidad."""


# =============================================================================
# 5. CLIENTE
# =============================================================================

# NUEVO: patrón sencillo de correo -> algo@dominio.ext (sin espacios).
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class Cliente(Entidad):
    """Representa a un cliente y protege sus datos mediante propiedades."""

    def __init__(self, identificador, nombre, correo, telefono):
        super().__init__(identificador)
        # Cada asignación pasa por su setter, que valida el dato.
        self.nombre = nombre
        self.correo = correo
        self.telefono = telefono

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        # NUEVO [REC-2]: tipo (str) + longitud mínima, con mensaje propio.
        try:
            self._nombre = validar_texto(valor, "El nombre", minimo=2)
        except DatosInvalidosError as error:
            raise DatosInvalidosError(
                f"No se pudo asignar el nombre del cliente. {error}") from error

    @property
    def correo(self):
        return self._correo

    @correo.setter
    def correo(self, valor):
        # NUEVO [REC-2]: primero tipo, luego formato con expresión regular.
        if not isinstance(valor, str) or not PATRON_CORREO.match(valor.strip()):
            raise DatosInvalidosError(
                "El correo electrónico no tiene un formato válido "
                f"(se recibió {valor!r})."
            )
        self._correo = valor.strip().lower()

    @property
    def telefono(self):
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        # NUEVO [REC-2]: se acepta texto o entero, pero no bool/None/float.
        if isinstance(valor, bool) or not isinstance(valor, (str, int)):
            raise DatosInvalidosError(
                "El teléfono debe ser texto o entero; se recibió "
                f"{type(valor).__name__}."
            )
        limpio = str(valor).replace(" ", "").replace("-", "")
        if not limpio.isdigit() or not 7 <= len(limpio) <= 15:
            raise DatosInvalidosError(
                "El teléfono debe contener entre 7 y 15 dígitos."
            )
        self._telefono = limpio

    def obtener_informacion(self):
        return f"Cliente {self.id}: {self.nombre} | {self.correo} | {self.telefono}"


# =============================================================================
# 6. SERVICIOS
# =============================================================================


class Servicio(Entidad, ABC):
    """Clase base abstracta para los servicios ofrecidos por Software FJ."""

    def __init__(self, identificador, nombre, tarifa, disponible=True):
        super().__init__(identificador)
        # NUEVO [REC-2]: tarifa validada por tipo, finitud y rango (> 0).
        validar_numero(tarifa, "La tarifa", minimo=0, estricto_minimo=True)
        self.nombre = validar_texto(nombre, "El nombre del servicio")
        self.tarifa = float(tarifa)
        if not isinstance(disponible, bool):
            raise DatosInvalidosError("'disponible' debe ser True o False.")
        self.disponible = disponible

    # NUEVO [REC-3]: métodos para cambiar la disponibilidad y poder probar
    # el caso "servicio no disponible".
    def deshabilitar(self):
        self.disponible = False
        logger.info("Servicio %s deshabilitado.", self.id)

    def habilitar(self):
        self.disponible = True
        logger.info("Servicio %s habilitado.", self.id)

    def validar_disponibilidad(self):
        if not self.disponible:
            raise ServicioNoDisponibleError(
                f"El servicio '{self.nombre}' no está disponible."
            )

    @staticmethod
    def _rechazar_extras_desconocidos(extras, permitidos):
        """NUEVO: si llega un parámetro opcional que el servicio no usa
        (por ejemplo 'persons' mal escrito) se informa en vez de ignorarlo."""
        desconocidos = set(extras) - set(permitidos)
        if desconocidos:
            raise DatosInvalidosError(
                f"Parámetros no reconocidos: {sorted(desconocidos)}."
            )

    # --- SOBRESCRITURA (override): cada subclase redefine este método ------
    @abstractmethod
    def calcular_costo(self, unidades, /, **extras):
        """Costo base (sin descuento ni impuesto). Cada servicio hijo lo
        sobrescribe con su propia fórmula (polimorfismo)."""

    # --- SOBRECARGA SIMULADA (overload) ------------------------------------
    # NUEVO [REC-6]: Python NO permite varios métodos con el mismo nombre y
    # distinta firma (el último reemplaza a los anteriores). Por eso la
    # sobrecarga se SIMULA con argumentos posicionales variables (*ajustes):
    #
    #   calcular_costo_total(unidades)                       -> costo base
    #   calcular_costo_total(unidades, descuento)            -> con descuento
    #   calcular_costo_total(unidades, descuento, impuesto)  -> con descuento
    #                                                           e impuesto
    #
    # NUEVO [REC-7]: el parámetro principal se llama 'unidades' (horas, días
    # o sesiones según el servicio) y es de SOLO POSICIÓN (la barra '/').
    # Antes se llamaba 'cantidad', igual que la opción de AlquilerEquipo, y
    # la llamada equipo.calcular_costo_total(2, cantidad=3) fallaba con
    # "got multiple values for argument 'cantidad'". Al ser solo posicional,
    # 'unidades' nunca puede chocar con una opción con nombre; si alguien lo
    # escribe como opción, se rechaza con DatosInvalidosError.
    #
    # Diferencia clave:
    #   * SOBRESCRITURA = calcular_costo (misma firma, distinta clase hija).
    #   * SOBRECARGA    = calcular_costo_total (misma clase, distinta
    #                     cantidad de argumentos).
    def calcular_costo_total(self, unidades, /, *ajustes, **extras):
        if len(ajustes) > 2:
            raise DatosInvalidosError(
                "Se recibieron demasiados parámetros: solo se admiten "
                "descuento e impuesto."
            )
        descuento = ajustes[0] if len(ajustes) >= 1 else 0
        impuesto = ajustes[1] if len(ajustes) == 2 else 0

        # NUEVO [REC-2]: tipos primero (texto, None, bool, NaN, infinito) y
        # rango después, ANTES de hacer ningún cálculo.
        validar_numero(descuento, "El descuento", minimo=0, maximo=100)
        validar_numero(impuesto, "El impuesto", minimo=0, maximo=100)

        subtotal = self.calcular_costo(unidades, **extras)  # polimórfico
        base = subtotal - subtotal * descuento / 100
        return round(base + base * impuesto / 100, 2)

    def obtener_informacion(self):
        estado = "disponible" if self.disponible else "NO disponible"
        return (f"{self.id} - {self.describir()} - "
                f"Tarifa: ${self.tarifa:,.0f} COP ({estado})")

    @abstractmethod
    def describir(self):
        """Texto descriptivo del servicio (se sobrescribe en cada hijo)."""


class ReservaSala(Servicio):
    """Servicio cuyo costo depende de las horas de uso de una sala."""

    def __init__(self, identificador, tarifa_hora, capacidad):
        super().__init__(identificador, "Reserva de sala", tarifa_hora)
        # NUEVO [REC-2]: capacidad entera, no bool, positiva.
        validar_numero(capacidad, "La capacidad", entero=True,
                       minimo=0, estricto_minimo=True)
        self.capacidad = capacidad

    def calcular_costo(self, horas, /, **extras):
        self._rechazar_extras_desconocidos(extras, {"personas"})
        self.validar_disponibilidad()
        validar_numero(horas, "Las horas", minimo=0, estricto_minimo=True)
        personas = extras.get("personas", 1)
        validar_numero(personas, "La cantidad de personas", entero=True,
                       minimo=1)
        if personas > self.capacidad:
            raise DatosInvalidosError(
                f"La cantidad de personas ({personas}) supera la capacidad "
                f"de la sala ({self.capacidad})."
            )
        return self.tarifa * horas

    def describir(self):
        return f"Reserva de sala (capacidad: {self.capacidad} personas)"


class AlquilerEquipo(Servicio):
    """Servicio de alquiler de equipos por día."""

    def __init__(self, identificador, tarifa_dia, tipo_equipo):
        super().__init__(identificador, "Alquiler de equipos", tarifa_dia)
        self.tipo_equipo = validar_texto(tipo_equipo, "El tipo de equipo")

    def calcular_costo(self, dias, /, **extras):
        self._rechazar_extras_desconocidos(extras, {"cantidad"})
        self.validar_disponibilidad()
        validar_numero(dias, "Los días", entero=True, minimo=1)
        cantidad = extras.get("cantidad", 1)
        validar_numero(cantidad, "La cantidad de equipos", entero=True,
                       minimo=1)
        return self.tarifa * dias * cantidad

    def describir(self):
        return f"Alquiler de equipos: {self.tipo_equipo}"


class AsesoriaEspecializada(Servicio):
    """Servicio de asesoría calculado por sesión."""

    def __init__(self, identificador, tarifa_sesion, especialidad):
        super().__init__(identificador, "Asesoría especializada", tarifa_sesion)
        self.especialidad = validar_texto(especialidad, "La especialidad")

    def calcular_costo(self, sesiones, /, **extras):
        self._rechazar_extras_desconocidos(extras, set())
        self.validar_disponibilidad()
        validar_numero(sesiones, "Las sesiones", entero=True, minimo=1)
        return self.tarifa * sesiones

    def describir(self):
        return f"Asesoría especializada en {self.especialidad}"


# =============================================================================
# 7. RESERVA
# =============================================================================


class Reserva(Entidad):
    """Relaciona un cliente con un servicio y controla el ciclo de reserva."""

    # NUEVO: constantes para los estados (evita errores de escritura).
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    PROCESADA = "PROCESADA"

    def __init__(self, identificador, cliente, servicio, duracion,
                 detalle=None):
        super().__init__(identificador)
        if not isinstance(cliente, Cliente):
            raise DatosInvalidosError("La reserva requiere un cliente válido.")
        if not isinstance(servicio, Servicio):
            raise DatosInvalidosError("La reserva requiere un servicio válido.")
        # NUEVO [REC-2]: duración validada por tipo (no texto/None/bool/NaN).
        validar_numero(duracion, "La duración", minimo=0, estricto_minimo=True)
        self.cliente = cliente
        self.servicio = servicio
        self.duracion = duracion
        self.detalle = detalle
        self.estado = self.PENDIENTE
        self.costo = 0.0

    def confirmar(self):
        if self.estado != self.PENDIENTE:
            raise OperacionNoPermitidaError(
                "Solo se pueden confirmar reservas pendientes."
            )
        self.servicio.validar_disponibilidad()
        self.estado = self.CONFIRMADA
        logger.info("Reserva %s confirmada para cliente %s.",
                    self.id, self.cliente.id)

    def cancelar(self):
        if self.estado not in (self.PENDIENTE, self.CONFIRMADA):
            raise OperacionNoPermitidaError(
                "La reserva no se puede cancelar en su estado actual."
            )
        self.estado = self.CANCELADA
        logger.info("Reserva %s cancelada.", self.id)

    def procesar(self, **extras):
        """Calcula el costo y marca la reserva como PROCESADA.

        NUEVO: los datos opcionales (personas=..., cantidad=...) se reciben
        por nombre (**extras) en lugar de *opciones posicionales, así no hay
        ambigüedad sobre qué significa cada valor.
        """
        if self.estado != self.CONFIRMADA:
            raise OperacionNoPermitidaError(
                "La reserva debe estar confirmada antes de procesarse."
            )
        try:
            costo = self.servicio.calcular_costo(self.duracion, **extras)
        except ErrorSistema as error:
            # Encadenamiento de excepciones: 'from error' conserva la causa.
            logger.exception("Error al procesar reserva %s.", self.id)
            raise ErrorSistema(
                "No fue posible calcular el costo de la reserva."
            ) from error
        else:
            # NUEVO: el costo se valida ANTES de guardarlo, y si es
            # inconsistente la reserva queda como estaba (CONFIRMADA).
            if (isinstance(costo, bool)
                    or not isinstance(costo, (int, float))
                    or not math.isfinite(costo) or costo <= 0):
                logger.error("Reserva %s: costo inconsistente (%r).",
                             self.id, costo)
                raise ErrorSistema("El cálculo produjo un costo inconsistente.")
            self.costo = float(costo)
            self.estado = self.PROCESADA
            logger.info("Reserva %s procesada. Costo: %.2f COP.",
                        self.id, self.costo)
            return self.costo
        finally:
            # Se ejecuta SIEMPRE (haya error o no).
            logger.info("Finalizó intento de procesamiento de reserva %s.",
                        self.id)

    def obtener_informacion(self):
        return (
            f"Reserva {self.id} | Cliente: {self.cliente.nombre} | "
            f"Servicio: {self.servicio.nombre} | Estado: {self.estado} | "
            f"Costo: ${self.costo:,.0f} COP"
        )


# =============================================================================
# 8. GESTOR DE LA APLICACIÓN
# =============================================================================


class SistemaSoftwareFJ:
    """Administra las listas internas de clientes, servicios y reservas."""

    def __init__(self):
        self.clientes = []
        self.servicios = []
        self.reservas = []

    def registrar_cliente(self, cliente):
        # NUEVO: se verifica el tipo del objeto recibido.
        if not isinstance(cliente, Cliente):
            raise DatosInvalidosError("Se esperaba un objeto Cliente.")
        if any(c.id == cliente.id for c in self.clientes):
            raise DatosInvalidosError("Ya existe un cliente con ese identificador.")
        self.clientes.append(cliente)
        logger.info("Cliente registrado: %s.", cliente.id)
        return cliente

    def registrar_servicio(self, servicio):
        if not isinstance(servicio, Servicio):
            raise DatosInvalidosError("Se esperaba un objeto Servicio.")
        if any(s.id == servicio.id for s in self.servicios):
            raise DatosInvalidosError("Ya existe un servicio con ese identificador.")
        self.servicios.append(servicio)
        logger.info("Servicio registrado: %s.", servicio.id)
        return servicio

    def crear_reserva(self, reserva):
        if not isinstance(reserva, Reserva):
            raise DatosInvalidosError("Se esperaba un objeto Reserva.")
        if any(r.id == reserva.id for r in self.reservas):
            raise DatosInvalidosError("Ya existe una reserva con ese identificador.")
        # NUEVO [REC-8]: antes solo se comparaban los identificadores, y una
        # reserva con otro cliente/servicio que tuviera el MISMO id (pero
        # datos distintos, p. ej. otra tarifa) se aceptaba. Ahora se exige
        # que sean exactamente los objetos registrados en el gestor.
        self._exigir_registrado(self.clientes, reserva.cliente, "cliente")
        self._exigir_registrado(self.servicios, reserva.servicio, "servicio")
        self.reservas.append(reserva)
        logger.info("Reserva creada: %s.", reserva.id)
        return reserva

    @staticmethod
    def _exigir_registrado(lista, objeto, etiqueta):
        """NUEVO [REC-8]: verifica que 'objeto' sea el MISMO objeto (no solo
        el mismo id) que está guardado en 'lista'.

        - Si no hay ninguno con ese id        -> ElementoNoEncontradoError.
        - Si hay uno con ese id pero es otro  -> DatosInvalidosError.
          objeto (datos distintos)
        'is' compara identidad (¿es el mismo objeto en memoria?), mientras
        que '==' o comparar ids solo diría que "se parecen".
        """
        for registrado in lista:
            if registrado.id == objeto.id:
                if registrado is not objeto:
                    raise DatosInvalidosError(
                        f"El {etiqueta} {objeto.id} de la reserva no es el "
                        f"objeto registrado en el sistema (mismo "
                        f"identificador, datos distintos)."
                    )
                return registrado
        raise ElementoNoEncontradoError(
            f"El {etiqueta} no está registrado en el sistema."
        )

    def nueva_reserva(self, identificador, id_cliente, id_servicio, duracion,
                      detalle=None):
        """NUEVO [REC-8]: forma recomendada de crear una reserva. Recibe
        solo IDENTIFICADORES, recupera del gestor los objetos registrados y
        construye la reserva con ellos; así no puede haber referencias
        falsas. Lanza ElementoNoEncontradoError si algún id no existe."""
        cliente = self.buscar_cliente(id_cliente)
        servicio = self.buscar_servicio(id_servicio)
        reserva = Reserva(identificador, cliente, servicio, duracion, detalle)
        return self.crear_reserva(reserva)

    def buscar_cliente(self, identificador):
        for cliente in self.clientes:
            if cliente.id == str(identificador):
                return cliente
        raise ElementoNoEncontradoError(f"No existe el cliente {identificador}.")

    # NUEVO: búsquedas equivalentes para servicios y reservas.
    def buscar_servicio(self, identificador):
        for servicio in self.servicios:
            if servicio.id == str(identificador):
                return servicio
        raise ElementoNoEncontradoError(f"No existe el servicio {identificador}.")

    def buscar_reserva(self, identificador):
        for reserva in self.reservas:
            if reserva.id == str(identificador):
                return reserva
        raise ElementoNoEncontradoError(f"No existe la reserva {identificador}.")

    def listar_reservas(self):
        return [reserva.obtener_informacion() for reserva in self.reservas]


# =============================================================================
# 9. DEMOSTRACIÓN Y PRUEBAS
# =============================================================================


class ServicioDefectuoso(Servicio):
    """Servicio de PRUEBA que calcula un costo inválido (0).
    Sirve para demostrar el manejo de 'cálculos inconsistentes' del anexo."""

    def calcular_costo(self, unidades, /, **extras):
        return 0

    def describir(self):
        return "Servicio defectuoso (solo para pruebas)"


def exigir(condicion, mensaje):
    """NUEVO [REC-9]: comprobación explícita de un valor o un estado.

    Se usa en lugar de 'assert' porque 'assert' se desactiva al ejecutar
    Python con la opción -O; esta función siempre se ejecuta.
    """
    if not condicion:
        raise AssertionError(mensaje)


def casi_igual(a, b):
    """NUEVO [REC-9]: compara costos con tolerancia de 1 centavo (los
    números decimales no siempre son exactos)."""
    return math.isclose(a, b, rel_tol=0, abs_tol=0.01)


class EjecutorPruebas:
    """Ejecuta cada operación de forma AISLADA y comprueba su resultado.

    Cada operación se ejecuta dentro de su propio try/except, de modo que:
      * un error esperado se captura, se registra en el log y se imprime;
      * un error INESPERADO también se captura y se registra, pero NO
        termina la demostración (la siguiente operación se ejecuta igual);
      * NUEVO [REC-9]: además de comprobar que ocurrió (o no) la excepción
        esperada, se ejecuta una función 'verificar' que comprueba valores
        concretos: costos, estados y cantidades de objetos registrados.
        Una operación solo cuenta como correcta si pasa AMBAS comprobaciones.
    """

    def __init__(self):
        self.resultados = []   # lista de (numero, descripcion, ok, verificada)
        self._numero = 0       # NUEVO: numeración automática de operaciones

    def ejecutar(self, descripcion, funcion, error_esperado=None,
                 verificar=None):
        """Ejecuta 'funcion'.

        error_esperado: None si se espera éxito; clase (o tupla) de
                        excepción si se espera que la lance.
        verificar:      función(salida) que lanza AssertionError (vía
                        exigir) si algún valor o estado no es el esperado.
                        'salida' es el resultado devuelto, o la excepción
                        capturada cuando se esperaba un error.
        """
        self._numero += 1
        numero = self._numero
        etiqueta = f"{numero:>2}. {descripcion}"
        salida = None
        correcto = False
        try:
            salida = funcion()
        except Exception as error:  # noqa: BLE001 - se aísla cada operación
            salida = error
            if error_esperado is not None and isinstance(error, error_esperado):
                logger.exception("Operación %s (error esperado): %s",
                                 numero, descripcion)
                causa = (f" [causa: {type(error.__cause__).__name__}]"
                         if error.__cause__ else "")
                print(f"{etiqueta}\n    ✔ Error controlado "
                      f"({type(error).__name__}): {error}{causa}")
                correcto = True
            else:
                logger.exception("Operación %s (ERROR INESPERADO): %s",
                                 numero, descripcion)
                print(f"{etiqueta}\n    ✘ Error inesperado "
                      f"({type(error).__name__}): {error}")
        else:
            if error_esperado is None:
                print(f"{etiqueta}\n    ✔ OK: {salida}")
                correcto = True
            else:
                logger.error("Operación %s: se esperaba %s y no ocurrió.",
                             numero, error_esperado)
                print(f"{etiqueta}\n    ✘ Se esperaba un error y no ocurrió.")

        # NUEVO [REC-9]: verificación explícita de valores y estados.
        if correcto and verificar is not None:
            try:
                verificar(salida)
            except Exception as error_verif:  # noqa: BLE001
                correcto = False
                logger.error("Operación %s: VERIFICACIÓN FALLIDA: %s",
                             numero, error_verif)
                print(f"    ✘ Verificación fallida: {error_verif}")
            else:
                print("    ✔ Verificado: valores y estados correctos")
        self.resultados.append(
            (numero, descripcion, correcto, verificar is not None))

        # [REC-5] Evidencia de continuidad tras CADA operación.
        logger.info("Operación %s finalizada; el sistema continúa activo.",
                    numero)
        return None if isinstance(salida, Exception) else salida

    def resumen(self):
        total = len(self.resultados)
        correctas = sum(1 for r in self.resultados if r[2])
        verificadas = sum(1 for r in self.resultados if r[3])
        print(f"\nOperaciones ejecutadas: {total} | "
              f"con resultado esperado: {correctas} | "
              f"fallidas: {total - correctas}")
        print(f"Operaciones con verificación explícita de valores/estados: "
              f"{verificadas} de {total}")
        for numero, descripcion, ok, _ in self.resultados:
            if not ok:
                print(f"  ✘ Falló la operación {numero}: {descripcion}")
        return correctas == total


def ejecutar_demostracion():
    sistema = SistemaSoftwareFJ()
    prueba = EjecutorPruebas()
    ctx = {}  # guarda los objetos creados para usarlos en operaciones siguientes

    # Se recuerda dónde termina el log ahora para mostrar al final solo las
    # líneas generadas en ESTA ejecución.
    posicion_log = RUTA_LOG.stat().st_size if RUTA_LOG.exists() else 0
    logger.info("===== INICIO DE LA DEMOSTRACIÓN =====")

    print("\n=== SISTEMA INTEGRAL SOFTWARE FJ ===")

    # ---- Verificadores reutilizables (NUEVO [REC-9]) ---------------------
    def contadores(c, s, r, campo=None):
        """Comprueba cuántos clientes, servicios y reservas hay registrados
        (un error NO debe haber guardado nada). Si se indica 'campo',
        comprueba además que el mensaje de error mencione ese dato."""
        def _verificar(salida):
            exigir(len(sistema.clientes) == c,
                   f"Clientes: se esperaban {c} y hay {len(sistema.clientes)}.")
            exigir(len(sistema.servicios) == s,
                   f"Servicios: se esperaban {s} y hay {len(sistema.servicios)}.")
            exigir(len(sistema.reservas) == r,
                   f"Reservas: se esperaban {r} y hay {len(sistema.reservas)}.")
            if campo is not None:
                exigir(campo in str(salida).lower(),
                       f"El mensaje de error debería mencionar '{campo}'.")
        return _verificar

    def reserva_es(clave, estado, costo):
        """Comprueba el estado y el costo de una reserva guardada en ctx."""
        def _verificar(_):
            r = ctx[clave]
            exigir(r.estado == estado,
                   f"Reserva {r.id}: estado esperado {estado}, "
                   f"obtenido {r.estado}.")
            exigir(casi_igual(r.costo, costo),
                   f"Reserva {r.id}: costo esperado {costo:,.2f}, "
                   f"obtenido {r.costo:,.2f}.")
        return _verificar

    def combinar(*verificadores):
        def _verificar(salida):
            for v in verificadores:
                v(salida)
        return _verificar

    # ======================= CLIENTES =======================
    print("\n--- Clientes ---")

    def op_cliente1():
        # Se envía correo con mayúsculas y teléfono con espacios para
        # comprobar que el sistema los normaliza.
        ctx["c1"] = sistema.registrar_cliente(
            Cliente("C001", "Ana Mosquera", "Ana@Email.com", "300 123 4567"))
        return ctx["c1"].obtener_informacion()

    def ver_cliente1(_):
        c = ctx["c1"]
        exigir(c.id == "C001", "El id del cliente debe ser C001.")
        exigir(c.nombre == "Ana Mosquera", "Nombre mal guardado.")
        exigir(c.correo == "ana@email.com",
               "El correo debe guardarse en minúsculas.")
        exigir(c.telefono == "3001234567",
               "El teléfono debe guardarse sin espacios.")
        contadores(1, 0, 0)(_)
    prueba.ejecutar("Registro válido de cliente C001 (normaliza correo y "
                    "teléfono)", op_cliente1, verificar=ver_cliente1)

    def op_cliente2():
        ctx["c2"] = sistema.registrar_cliente(
            Cliente("C002", "Carlos Rentería", "carlos@email.com", "3107654321"))
        return ctx["c2"].obtener_informacion()
    prueba.ejecutar("Registro válido de cliente C002", op_cliente2,
                    verificar=combinar(
                        lambda _: exigir(ctx["c2"].id == "C002",
                                         "El id debe ser C002."),
                        contadores(2, 0, 0)))

    # Cada validación se prueba POR SEPARADO: los otros dos datos son
    # correctos, así el error solo puede venir del dato probado, y se
    # comprueba que el mensaje mencione ese dato.
    prueba.ejecutar(
        "Cliente con NOMBRE inválido ('X'); correo y teléfono válidos",
        lambda: Cliente("C003", "X", "ok@email.com", "3001112233"),
        DatosInvalidosError, contadores(2, 0, 0, campo="nombre"))
    prueba.ejecutar(
        "Cliente con CORREO inválido; nombre y teléfono válidos",
        lambda: Cliente("C004", "Laura Pérez", "correo-invalido", "3001112233"),
        DatosInvalidosError, contadores(2, 0, 0, campo="correo"))
    prueba.ejecutar(
        "Cliente con TELÉFONO inválido ('123'); nombre y correo válidos",
        lambda: Cliente("C005", "Mario Gómez", "mario@email.com", "123"),
        DatosInvalidosError, contadores(2, 0, 0, campo="teléfono"))
    prueba.ejecutar(
        "Cliente con NOMBRE de tipo incorrecto (None)",
        lambda: Cliente("C006", None, "ok@email.com", "3001112233"),
        DatosInvalidosError, contadores(2, 0, 0, campo="nombre"))
    prueba.ejecutar(
        "Cliente duplicado (mismo identificador C001)",
        lambda: sistema.registrar_cliente(
            Cliente("C001", "Otra Persona", "otra@email.com", "3009998877")),
        DatosInvalidosError,
        combinar(contadores(2, 0, 0),
                 lambda _: exigir(sistema.buscar_cliente("C001") is ctx["c1"],
                                  "El cliente C001 original fue reemplazado.")))

    # ======================= SERVICIOS =======================
    print("\n--- Servicios ---")

    def op_sala():
        ctx["sala"] = sistema.registrar_servicio(ReservaSala("S001", 50000, 20))
        return ctx["sala"].describir()
    prueba.ejecutar(
        "Registro de servicio: reserva de sala", op_sala,
        verificar=combinar(
            lambda _: exigir(ctx["sala"].tarifa == 50000
                             and ctx["sala"].capacidad == 20,
                             "Tarifa o capacidad de la sala mal guardadas."),
            contadores(2, 1, 0)))

    def op_equipo():
        ctx["equipo"] = sistema.registrar_servicio(
            AlquilerEquipo("S002", 80000, "Video beam"))
        return ctx["equipo"].describir()
    prueba.ejecutar(
        "Registro de servicio: alquiler de equipo", op_equipo,
        verificar=combinar(
            lambda _: exigir(ctx["equipo"].tarifa == 80000
                             and ctx["equipo"].tipo_equipo == "Video beam",
                             "Tarifa o tipo de equipo mal guardados."),
            contadores(2, 2, 0)))

    def op_asesoria():
        ctx["asesoria"] = sistema.registrar_servicio(
            AsesoriaEspecializada("S003", 120000, "Desarrollo de software"))
        return ctx["asesoria"].describir()
    prueba.ejecutar(
        "Registro de servicio: asesoría", op_asesoria,
        verificar=combinar(
            lambda _: exigir(ctx["asesoria"].tarifa == 120000,
                             "Tarifa de la asesoría mal guardada."),
            contadores(2, 3, 0)))

    # Creación INCORRECTA de servicios: no debe quedar nada registrado.
    prueba.ejecutar(
        "Servicio con tarifa de tipo texto ('gratis')",
        lambda: ReservaSala("S004", "gratis", 10),
        DatosInvalidosError, contadores(2, 3, 0, campo="tarifa"))
    prueba.ejecutar(
        "Servicio con capacidad booleana (True)",
        lambda: ReservaSala("S005", 50000, True),
        DatosInvalidosError, contadores(2, 3, 0, campo="capacidad"))
    prueba.ejecutar(
        "Servicio con tarifa NaN (valor no finito)",
        lambda: AlquilerEquipo("S006", float("nan"), "Portátil"),
        DatosInvalidosError, contadores(2, 3, 0, campo="tarifa"))
    prueba.ejecutar(
        "Alquiler sin tipo de equipo (vacío)",
        lambda: AlquilerEquipo("S007", 80000, "   "),
        DatosInvalidosError, contadores(2, 3, 0, campo="equipo"))
    prueba.ejecutar(
        "Instanciar la clase abstracta Servicio directamente",
        lambda: Servicio("S008", "Genérico", 1000),
        TypeError, contadores(2, 3, 0))

    # ======================= RESERVAS =======================
    print("\n--- Reservas ---")

    def op_reserva_valida():
        r = sistema.crear_reserva(
            Reserva("R001", ctx["c1"], ctx["sala"], 3, "Reunión de equipo"))
        r.confirmar()
        ctx["r1"] = r
        return f"Reserva {r.id} {r.estado}"
    prueba.ejecutar("Reserva válida de sala + confirmación", op_reserva_valida,
                    verificar=combinar(reserva_es("r1", Reserva.CONFIRMADA, 0),
                                       contadores(2, 3, 1)))

    def op_procesar():
        return ctx["r1"].procesar(personas=10)  # sala con capacidad para 20
    prueba.ejecutar(
        "Procesamiento correcto (3 h x $50.000 = $150.000)", op_procesar,
        verificar=combinar(
            lambda costo: exigir(casi_igual(costo, 150000),
                                 f"Costo esperado 150000, obtenido {costo}."),
            reserva_es("r1", Reserva.PROCESADA, 150000)))

    def op_reserva_sobrecupo():
        r = sistema.crear_reserva(Reserva("R002", ctx["c2"], ctx["sala"], 2))
        r.confirmar()
        ctx["r2"] = r
        r.procesar(personas=50)   # supera la capacidad de 20
    prueba.ejecutar(
        "Procesar reserva con más personas que la capacidad (50 > 20)",
        op_reserva_sobrecupo, ErrorSistema,
        combinar(
            # Encadenamiento: la causa original debe conservarse.
            lambda e: exigir(isinstance(e.__cause__, DatosInvalidosError),
                             "La excepción debe encadenar su causa (from)."),
            # El error NO debe cambiar el estado ni el costo de la reserva.
            reserva_es("r2", Reserva.CONFIRMADA, 0),
            contadores(2, 3, 2)))

    prueba.ejecutar(
        "CONTINUIDAD: reintentar la misma reserva con datos válidos "
        "(2 h x $50.000 = $100.000)",
        lambda: ctx["r2"].procesar(personas=5),
        verificar=combinar(
            lambda costo: exigir(casi_igual(costo, 100000),
                                 f"Costo esperado 100000, obtenido {costo}."),
            reserva_es("r2", Reserva.PROCESADA, 100000)))

    def op_cliente_no_registrado():
        externo = Cliente("C999", "Cliente Externo", "externo@email.com",
                          "3201234567")
        sistema.crear_reserva(Reserva("R003", externo, ctx["equipo"], 2))
    prueba.ejecutar("Reserva con cliente NO registrado",
                    op_cliente_no_registrado, ElementoNoEncontradoError,
                    contadores(2, 3, 2))

    # NUEVO [REC-8]: casos del tutor. Mismo identificador pero OTRO objeto
    # con datos distintos: antes se aceptaban porque solo se comparaba el id.
    def op_cliente_impostor():
        impostor = Cliente("C001", "Persona Distinta", "otra@email.com",
                           "3119998877")
        sistema.crear_reserva(Reserva("R010", impostor, ctx["equipo"], 2))
    prueba.ejecutar(
        "Reserva con CLIENTE distinto pero con el mismo id (C001)",
        op_cliente_impostor, DatosInvalidosError,
        combinar(
            contadores(2, 3, 2, campo="cliente"),
            lambda _: exigir(sistema.buscar_cliente("C001") is ctx["c1"]
                             and ctx["c1"].nombre == "Ana Mosquera",
                             "El cliente registrado fue alterado.")))

    def op_servicio_impostor():
        falso = ReservaSala("S001", 1, 5)   # mismo id que la sala, tarifa $1
        sistema.crear_reserva(Reserva("R011", ctx["c1"], falso, 2))
    prueba.ejecutar(
        "Reserva con SERVICIO distinto pero con el mismo id (S001, tarifa $1)",
        op_servicio_impostor, DatosInvalidosError,
        combinar(
            contadores(2, 3, 2, campo="servicio"),
            lambda _: exigir(
                sistema.buscar_servicio("S001") is ctx["sala"]
                and ctx["sala"].tarifa == 50000,
                "El servicio registrado fue alterado.")))

    # NUEVO [REC-8]: forma recomendada: el gestor construye la reserva con
    # los objetos que YA tiene registrados (recibe solo identificadores).
    def op_nueva_reserva():
        r = sistema.nueva_reserva("R009", "C001", "S002", 2,
                                  "Proyector para taller")
        ctx["r9"] = r
        r.confirmar()
        return r.procesar(cantidad=3)   # 2 días x 3 equipos x $80.000
    prueba.ejecutar(
        "Reserva creada con nueva_reserva(): 2 días x 3 equipos x $80.000 "
        "= $480.000", op_nueva_reserva,
        verificar=combinar(
            lambda costo: exigir(casi_igual(costo, 480000),
                                 f"Costo esperado 480000, obtenido {costo}."),
            lambda _: exigir(
                ctx["r9"].cliente is sistema.buscar_cliente("C001")
                and ctx["r9"].servicio is ctx["equipo"],
                "La reserva debe usar los objetos registrados."),
            reserva_es("r9", Reserva.PROCESADA, 480000),
            contadores(2, 3, 3)))

    prueba.ejecutar(
        "Reserva con duración inválida (0)",
        lambda: Reserva("R004", ctx["c2"], ctx["asesoria"], 0),
        DatosInvalidosError, contadores(2, 3, 3, campo="duración"))
    prueba.ejecutar(
        "Reserva con duración de tipo texto ('dos')",
        lambda: Reserva("R005", ctx["c2"], ctx["asesoria"], "dos"),
        DatosInvalidosError, contadores(2, 3, 3, campo="duración"))

    def op_cancelar():
        r = sistema.crear_reserva(Reserva("R006", ctx["c2"], ctx["equipo"], 2))
        r.cancelar()
        ctx["r6"] = r
        return f"Reserva {r.id} {r.estado}"
    prueba.ejecutar("Cancelación válida de reserva", op_cancelar,
                    verificar=combinar(reserva_es("r6", Reserva.CANCELADA, 0),
                                       contadores(2, 3, 4)))

    prueba.ejecutar(
        "Procesar una reserva CANCELADA", lambda: ctx["r6"].procesar(),
        OperacionNoPermitidaError,
        combinar(reserva_es("r6", Reserva.CANCELADA, 0),
                 contadores(2, 3, 4)))

    # ================= SERVICIO NO DISPONIBLE =================
    print("\n--- Servicio no disponible ---")

    def op_no_disponible():
        r = sistema.crear_reserva(Reserva("R007", ctx["c1"], ctx["asesoria"], 2))
        ctx["r7"] = r
        ctx["asesoria"].deshabilitar()
        r.confirmar()   # debe fallar: el servicio está deshabilitado
    prueba.ejecutar(
        "Confirmar reserva de un servicio NO disponible",
        op_no_disponible, ServicioNoDisponibleError,
        combinar(reserva_es("r7", Reserva.PENDIENTE, 0),
                 lambda _: exigir(ctx["asesoria"].disponible is False,
                                  "El servicio debería seguir deshabilitado."),
                 contadores(2, 3, 5)))

    def op_rehabilitar():
        ctx["asesoria"].habilitar()
        ctx["r7"].confirmar()
        return ctx["r7"].procesar()   # 2 sesiones x $120.000
    prueba.ejecutar(
        "CONTINUIDAD: habilitar el servicio y completar la reserva "
        "(2 sesiones x $120.000 = $240.000)", op_rehabilitar,
        verificar=combinar(
            lambda costo: exigir(casi_igual(costo, 240000),
                                 f"Costo esperado 240000, obtenido {costo}."),
            reserva_es("r7", Reserva.PROCESADA, 240000),
            lambda _: exigir(ctx["asesoria"].disponible is True,
                             "El servicio debería estar habilitado.")))

    # ============ CÁLCULO DE COSTOS (sobrecarga simulada) ============
    print("\n--- Cálculo de costos (sobrecarga simulada) ---")

    def variantes(clave, unidades, **extras):
        """Ejecuta las TRES variantes de calcular_costo_total."""
        servicio = ctx[clave]
        return (servicio.calcular_costo_total(unidades, **extras),
                servicio.calcular_costo_total(unidades, 10, **extras),
                servicio.calcular_costo_total(unidades, 10, 19, **extras))

    def ver_variantes(esperados):
        nombres = ("base", "con 10% de descuento",
                   "con 10% de descuento y 19% de impuesto")

        def _verificar(salida):
            for nombre, obtenido, esperado in zip(nombres, salida, esperados):
                exigir(casi_igual(obtenido, esperado),
                       f"{nombre}: esperado {esperado:,.2f}, "
                       f"obtenido {obtenido:,.2f}.")
        return _verificar

    # NUEVO [REC-7]: las variantes se comprueban con LOS TRES servicios.
    prueba.ejecutar(
        "Variantes de costo con la SALA (2 h): 100.000 / 90.000 / 107.100",
        lambda: variantes("sala", 2),
        verificar=ver_variantes((100000, 90000, 107100)))
    prueba.ejecutar(
        "Variantes de costo con el EQUIPO (2 días, cantidad=3): "
        "480.000 / 432.000 / 514.080",
        lambda: variantes("equipo", 2, cantidad=3),   # caso exacto del tutor
        verificar=ver_variantes((480000, 432000, 514080)))
    prueba.ejecutar(
        "Variantes de costo con la ASESORÍA (3 sesiones): "
        "360.000 / 324.000 / 385.560",
        lambda: variantes("asesoria", 3),
        verificar=ver_variantes((360000, 324000, 385560)))

    prueba.ejecutar(
        "Pasar 'unidades' como opción con nombre (conflicto de parámetros)",
        lambda: ctx["equipo"].calcular_costo_total(2, unidades=5),
        DatosInvalidosError,
        combinar(contadores(2, 3, 5, campo="unidades")))
    prueba.ejecutar(
        "Equipo con cantidad=0 (opción inválida)",
        lambda: ctx["equipo"].calcular_costo_total(2, cantidad=0),
        DatosInvalidosError, contadores(2, 3, 5, campo="cantidad"))
    prueba.ejecutar(
        "Sala con más personas que la capacidad en calcular_costo_total",
        lambda: ctx["sala"].calcular_costo_total(2, personas=50),
        DatosInvalidosError, contadores(2, 3, 5, campo="capacidad"))
    prueba.ejecutar(
        "Descuento de tipo texto ('diez')",
        lambda: ctx["sala"].calcular_costo_total(2, "diez"),
        DatosInvalidosError, contadores(2, 3, 5, campo="descuento"))
    prueba.ejecutar(
        "Descuento None",
        lambda: ctx["sala"].calcular_costo_total(2, None),
        DatosInvalidosError, contadores(2, 3, 5, campo="descuento"))
    prueba.ejecutar(
        "Impuesto NaN (no finito)",
        lambda: ctx["sala"].calcular_costo_total(2, 10, float("nan")),
        DatosInvalidosError, contadores(2, 3, 5, campo="impuesto"))
    prueba.ejecutar(
        "Descuento booleano (True)",
        lambda: ctx["sala"].calcular_costo_total(2, True),
        DatosInvalidosError, contadores(2, 3, 5, campo="descuento"))
    prueba.ejecutar(
        "Descuento fuera de rango (150%)",
        lambda: ctx["sala"].calcular_costo_total(2, 150),
        DatosInvalidosError, contadores(2, 3, 5, campo="descuento"))
    prueba.ejecutar(
        "Demasiados parámetros (3 ajustes)",
        lambda: ctx["sala"].calcular_costo_total(2, 10, 19, 5),
        DatosInvalidosError, contadores(2, 3, 5, campo="demasiados"))
    prueba.ejecutar(
        "Unidades (horas) de tipo texto",
        lambda: ctx["sala"].calcular_costo_total("3"),
        DatosInvalidosError, contadores(2, 3, 5, campo="horas"))

    # ================ CÁLCULO INCONSISTENTE ================
    def op_costo_inconsistente():
        defectuoso = sistema.registrar_servicio(
            ServicioDefectuoso("S099", "Defectuoso", 1000))
        r = sistema.crear_reserva(Reserva("R008", ctx["c1"], defectuoso, 1))
        ctx["r8"] = r
        r.confirmar()
        r.procesar()
    prueba.ejecutar(
        "Cálculo inconsistente (costo 0 devuelto por el servicio)",
        op_costo_inconsistente, ErrorSistema,
        combinar(reserva_es("r8", Reserva.CONFIRMADA, 0),
                 contadores(2, 4, 6, campo="inconsistente")))

    # ======================= BÚSQUEDAS =======================
    prueba.ejecutar(
        "Buscar cliente inexistente",
        lambda: sistema.buscar_cliente("C404"),
        ElementoNoEncontradoError, contadores(2, 4, 6, campo="c404"))

    prueba.ejecutar(
        "CONTINUIDAD FINAL: buscar cliente existente",
        lambda: sistema.buscar_cliente("C001").obtener_informacion(),
        verificar=lambda texto: exigir("Ana Mosquera" in texto,
                                       "No se encontró a Ana Mosquera."))

    # NUEVO [REC-9]: tabla final de estados y costos esperados. Si alguna
    # reserva terminó en un estado o costo distinto, esta operación falla.
    def op_consistencia_final():
        esperado = {
            "R001": (Reserva.PROCESADA, 150000),
            "R002": (Reserva.PROCESADA, 100000),
            "R006": (Reserva.CANCELADA, 0),
            "R007": (Reserva.PROCESADA, 240000),
            "R008": (Reserva.CONFIRMADA, 0),
            "R009": (Reserva.PROCESADA, 480000),
        }
        for id_reserva, (estado, costo) in esperado.items():
            r = sistema.buscar_reserva(id_reserva)
            exigir(r.estado == estado and casi_igual(r.costo, costo),
                   f"{id_reserva}: esperado {estado}/{costo:,.0f}, "
                   f"obtenido {r.estado}/{r.costo:,.0f}.")
        exigir(len(esperado) == len(sistema.reservas),
               "Hay reservas que no estaban previstas.")
        return f"{len(esperado)} reservas con estado y costo correctos"
    prueba.ejecutar("Consistencia final de estados y costos de todas las "
                    "reservas", op_consistencia_final,
                    verificar=contadores(2, 4, 6))

    # ======================= RESUMEN =======================
    print("\n--- RESUMEN DE RESERVAS ---")
    for elemento in sistema.listar_reservas():
        print(elemento)
    print(f"\nClientes: {len(sistema.clientes)} | "
          f"Servicios: {len(sistema.servicios)} | "
          f"Reservas: {len(sistema.reservas)}")

    todo_ok = prueba.resumen()
    logger.info("===== FIN DE LA DEMOSTRACIÓN (todo esperado: %s) =====", todo_ok)

    # Evidencia del archivo de logs: solo las líneas con fecha (la primera
    # de cada registro), no los traceback.
    print(f"\n--- EXTRACTO DEL LOG ({RUTA_LOG.name}) ---")
    for h in logger.handlers:
        h.flush()
    with open(RUTA_LOG, "r", encoding="utf-8") as archivo:
        archivo.seek(posicion_log)
        lineas = [l.rstrip() for l in archivo
                  if re.match(r"^\d{4}-\d{2}-\d{2} ", l)]
    for linea in lineas:
        print(linea)
    print(f"\nRuta completa del log: {RUTA_LOG}")
    return todo_ok


if __name__ == "__main__":
    try:
        ejecutar_demostracion()
    except Exception:
        # Última barrera: evita que un error inesperado quede sin registro.
        # (Cada operación ya está aislada en EjecutorPruebas, por lo que
        # aquí solo llegarían fallos fuera de las operaciones.)
        logger.exception("Error inesperado en la ejecución principal.")
        raise
