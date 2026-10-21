"""Departmental Generator Agents for Milestone 9 - Part 2 (Response Generation)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("trackflow.rfp_intake.generators")


class BaseDepartmentGenerator:
    """Base class for departmental response generation."""

    def __init__(self, department_id: str, department_name: str, contact_person: str):
        self.department_id = department_id
        self.department_name = department_name
        self.contact_person = contact_person

    def _resolve_currency(self, client_country: str | None, metadata_currency: str | None) -> str:
        """Resolve proper currency matching §5 business guidelines."""
        norm_country = (client_country or "").strip().lower()
        if "spain" in norm_country or "españa" in norm_country:
            return "EUR"
        if "usa" in norm_country or "united states" in norm_country:
            return "USD"
        return metadata_currency or "EUR"

    def generate(
        self,
        *,
        key_aspects: dict[str, Any],
        shared_metadata: dict[str, Any],
        feedback_for_generator: str | None = None,
        iteration: int = 1,
    ) -> str:
        raise NotImplementedError


class WarehouseProposalGenerator(BaseDepartmentGenerator):
    """Generator Agent for Warehouse Operations (Ana Whitfield)."""

    def __init__(self):
        super().__init__(
            department_id="warehouse",
            department_name="Warehouse Operations",
            contact_person="Ana Whitfield",
        )

    def generate(
        self,
        *,
        key_aspects: dict[str, Any],
        shared_metadata: dict[str, Any],
        feedback_for_generator: str | None = None,
        iteration: int = 1,
    ) -> str:
        client_name = shared_metadata.get("client_name") or "Cliente"
        client_country = shared_metadata.get("client_country") or "Spain"
        currency = self._resolve_currency(client_country, shared_metadata.get("currency"))
        curr_symbol = "€" if currency == "EUR" else "$"
        monthly_volume = shared_metadata.get("monthly_volume") or 5000

        # Base pricing per warehouse operations specs
        pallet_rate = 14.50 if currency == "EUR" else 16.00
        inbound_rate = 3.20 if currency == "EUR" else 3.50
        pick_pack_rate = 2.10 if currency == "EUR" else 2.30

        # Draft construction
        draft = f"""### Propuesta Económica y Técnica: Warehouse Operations
**Responsable del Departamento:** {self.contact_person}  
**Cliente:** {client_name} ({client_country})  
**Moneda Oficial de Cotización:** {currency} ({curr_symbol})

#### 1. Capacidad de Almacenamiento y Operaciones de Almacén
TrackFlow pone a disposición de {client_name} su moderna infraestructura logística con capacidad garantizada para gestión de stock, recepción de mercancía y preparación de pedidos. La operativa contempla una capacidad inicial estimada para soportar un volumen mensual de {monthly_volume:,} unidades y almacenamiento en estanterías estándar y dinámicas.

- **Almacenamiento mensual por pallet:** {curr_symbol}{pallet_rate:.2f} / mes
- **Recepción e inspección de inbound por bulto/pallet:** {curr_symbol}{inbound_rate:.2f}
- **Preparación de pedidos (Pick & Pack - primer ítem):** {curr_symbol}{pick_pack_rate:.2f}
- **Ítem adicional en mismo paquete:** {curr_symbol}0.45

#### 2. Plazos de Onboarding y Coordinación Operativa
El proceso integral de **onboarding e integración con el WMS** se completará en un plazo garantizado de 10 días hábiles desde la firma del acuerdo. Durante este periodo se configurarán los perfiles SKU, integraciones API y validación de stock inicial.

#### 3. Compromiso de Calidad y SLA Operativo
TrackFlow garantiza un **SLA de entrega a tiempo del 98.5%** en la expedición y preparación de pedidos dentro de la ventana de corte acordada (pedidos recibidos antes de las 14:00 se expiden el mismo día).

#### 4. Tabla de Descuentos por Volumen (Almacenamiento y Manipulación)
A continuación se detalla la escala de descuentos por volumen para {client_name}:

| Rango de Volumen Mensual (Unidades) | Descuento en Almacenamiento | Descuento en Picking | Tarifa Efectiva Pick&Pack ({currency}) |
| :--- | :--- | :--- | :--- |
| 1 - 2.500 unidades | Tarifa base (0%) | 0% | {curr_symbol}{pick_pack_rate:.2f} |
| 2.501 - 5.000 unidades | 5% de descuento | 4% | {curr_symbol}{pick_pack_rate * 0.96:.2f} |
| 5.001 - 10.000 unidades | 10% de descuento | 8% | {curr_symbol}{pick_pack_rate * 0.92:.2f} |
| > 10.000 unidades | 15% de descuento | 12% | {curr_symbol}{pick_pack_rate * 0.88:.2f} |

Esta estructura asegura escalabilidad y eficiencia operativa alineada al crecimiento previsto del negocio.
"""
        return draft.strip()


class LastMileProposalGenerator(BaseDepartmentGenerator):
    """Generator Agent for Last Mile and Carrier Management (Carlos Vega)."""

    def __init__(self):
        super().__init__(
            department_id="lastmile",
            department_name="Last Mile and Carrier Management",
            contact_person="Carlos Vega",
        )

    def generate(
        self,
        *,
        key_aspects: dict[str, Any],
        shared_metadata: dict[str, Any],
        feedback_for_generator: str | None = None,
        iteration: int = 1,
    ) -> str:
        client_name = shared_metadata.get("client_name") or "Cliente"
        client_country = shared_metadata.get("client_country") or "Spain"
        currency = self._resolve_currency(client_country, shared_metadata.get("currency"))
        curr_symbol = "€" if currency == "EUR" else "$"
        monthly_volume = shared_metadata.get("monthly_volume") or 5000

        base_std_shipment = 4.80 if currency == "EUR" else 5.50
        base_exp_shipment = 7.90 if currency == "EUR" else 8.90

        draft = f"""### Propuesta Económica y Técnica: Last Mile & Carrier Management
**Responsable del Departamento:** {self.contact_person}  
**Cliente:** {client_name} ({client_country})  
**Moneda Oficial de Cotización:** {currency} ({curr_symbol})

#### 1. Cobertura de Transporte y Opciones de Transportistas por Destino
TrackFlow ofrece una solución multicarrier unificada para la distribución capilar de los envíos de {client_name}. Gestionamos de extremo a extremo la selección inteligente del transportista idóneo según código postal, peso y urgencia, ofreciendo una experiencia de entrega fluida con portal de seguimiento para el destinatario.

- **Servicio Estándar Nacional (24-48h):** {curr_symbol}{base_std_shipment:.2f} por envío
- **Servicio Express Prioritario (24h garantizado):** {curr_symbol}{base_exp_shipment:.2f} por envío
- **Suplemento de entrega con firma / seguro básico:** {curr_symbol}0.75 por paquete
- **Cobertura geográfica:** Red de transportistas de primer nivel con cobertura completa en todo el territorio de {client_country} e islas/zonas periféricas.

*Nota de transparencia comercial: Todas las tarifas expuestas corresponden al precio final cerrado ofrecido al cliente.*

#### 2. Compromiso de Calidad y SLA de Entrega
TrackFlow asume formalmente un **SLA de entrega a tiempo del 99.0%** en envíos estándar y prioritarios, auditado semanalmente a través de nuestra API unificada de tracking. En caso de incidencia en ruta, el protocolo de resolución se activa en menos de 2 horas.

#### 3. Tabla de Descuentos por Volumen (Envíos de Última Milla)
Se aplica la siguiente tabla de descuentos por volumen sobre el coste por envío mensual:

| Volumen Mensual de Envíos | Descuento Aplicable | Tarifa Estándar Final ({currency}) | Tarifa Express Final ({currency}) |
| :--- | :--- | :--- | :--- |
| 1 - 1.500 envíos/mes | 0% (Base) | {curr_symbol}{base_std_shipment:.2f} | {curr_symbol}{base_exp_shipment:.2f} |
| 1.501 - 5.000 envíos/mes | 6% de descuento | {curr_symbol}{base_std_shipment * 0.94:.2f} | {curr_symbol}{base_exp_shipment * 0.94:.2f} |
| 5.001 - 10.000 envíos/mes | 12% de descuento | {curr_symbol}{base_std_shipment * 0.88:.2f} | {curr_symbol}{base_exp_shipment * 0.88:.2f} |
| > 10.000 envíos/mes | 18% de descuento | {curr_symbol}{base_std_shipment * 0.82:.2f} | {curr_symbol}{base_exp_shipment * 0.82:.2f} |

Esta estructura tarifaria garantiza competitividad de costes y máxima fiabilidad operativa para el crecimiento proyectado de {monthly_volume:,} envíos.
"""
        return draft.strip()


class ReverseLogisticsProposalGenerator(BaseDepartmentGenerator):
    """Generator Agent for Reverse Logistics (Sofía Ramos)."""

    def __init__(self):
        super().__init__(
            department_id="reverse",
            department_name="Reverse Logistics",
            contact_person="Sofía Ramos",
        )

    def generate(
        self,
        *,
        key_aspects: dict[str, Any],
        shared_metadata: dict[str, Any],
        feedback_for_generator: str | None = None,
        iteration: int = 1,
    ) -> str:
        client_name = shared_metadata.get("client_name") or "Cliente"
        client_country = shared_metadata.get("client_country") or "Spain"
        currency = self._resolve_currency(client_country, shared_metadata.get("currency"))
        curr_symbol = "€" if currency == "EUR" else "$"

        base_return_handling = 4.20 if currency == "EUR" else 4.80

        draft = f"""### Propuesta Económica y Técnica: Reverse Logistics
**Responsable del Departamento:** {self.contact_person}  
**Cliente:** {client_name} ({client_country})  
**Moneda Oficial de Cotización:** {currency} ({curr_symbol})

#### 1. Flujo y Procesamiento de Devoluciones
El departamento de Logística Inversa de TrackFlow proporciona una gestión integral de retornos para {client_name}, que comprende la recepción del paquete devuelto, verificación de etiquetas, inspección asistida por criterios de calidad y reubicación en inventario disponible o desecho según las políticas acordadas.

- **Recepción y registro de devolución:** {curr_symbol}{base_return_handling:.2f} por unidad
- **Inspección técnica y re-embolsado básico:** {curr_symbol}1.30 por ítem
- **Gestión de residuos / donación certificada:** {curr_symbol}0.60 por unidad

#### 2. Plazos de Procesamiento y SLA Operativo
Conforme a las políticas operativas de TrackFlow y los estándares de control de calidad, el **tiempo de procesamiento de devoluciones es de 48 a 72 horas hábiles** desde la llegada física de la mercancía al almacén central. TrackFlow establece un plazo de revisión e inspección exhaustiva de entre 48 y 72 horas hábiles para garantizar la máxima rigurosidad técnica.

Asimismo, TrackFlow se compromete a mantener un **SLA de entrega a tiempo del 98.0%** en la reposición de mercancía apta en inventario activo dentro de dicho margen temporal.

#### 3. Tabla de Descuentos por Volumen (Procesamiento de Devoluciones)
Tabla de descuentos por volumen aplicables a las unidades gestionadas mensualmente:

| Devoluciones Mensuales Procesadas | Descuento en Procesamiento | Tarifa Neta de Devolución ({currency}) |
| :--- | :--- | :--- |
| 1 - 300 retornos/mes | 0% (Base) | {curr_symbol}{base_return_handling:.2f} |
| 301 - 1.000 retornos/mes | 5% de descuento | {curr_symbol}{base_return_handling * 0.95:.2f} |
| 1.001 - 2.500 retornos/mes | 10% de descuento | {curr_symbol}{base_return_handling * 0.90:.2f} |
| > 2.500 retornos/mes | 15% de descuento | {curr_symbol}{base_return_handling * 0.85:.2f} |

Esta solución asegura trazabilidad absoluta del estado de cada retorno y minimiza el impacto económico de la logística inversa.
"""
        return draft.strip()


_GENERATORS: dict[str, BaseDepartmentGenerator] = {
    "warehouse": WarehouseProposalGenerator(),
    "lastmile": LastMileProposalGenerator(),
    "reverse": ReverseLogisticsProposalGenerator(),
}


def get_generator_for_department(department_id: str) -> BaseDepartmentGenerator:
    """Retrieve the dedicated generator agent for an active department."""
    if department_id in _GENERATORS:
        return _GENERATORS[department_id]
    # Fallback generator for unexpected department IDs
    return BaseDepartmentGenerator(
        department_id=department_id,
        department_name=department_id.capitalize(),
        contact_person="Responsable Asignado",
    )


def generate_department_draft(
    *,
    department_id: str,
    key_aspects: dict[str, Any],
    shared_metadata: dict[str, Any],
    feedback_for_generator: str | None = None,
    iteration: int = 1,
) -> str:
    """Execute generator agent to produce department proposal draft."""
    gen = get_generator_for_department(department_id)
    return gen.generate(
        key_aspects=key_aspects,
        shared_metadata=shared_metadata,
        feedback_for_generator=feedback_for_generator,
        iteration=iteration,
    )
