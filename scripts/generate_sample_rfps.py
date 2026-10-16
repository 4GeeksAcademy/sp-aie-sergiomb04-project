"""Generate the 3 official TrackFlow seed RFP PDFs for Milestone 9 testing.

Creates:
1. CONTEXT-trackflow-request-1.pdf (Formal RFP - ModaViva, Spain, EUR, warehouse + reverse, no lastmile)
2. CONTEXT-trackflow-request-2.pdf (Informal RFP - Luna Cosmetics, USA/LA, USD, warehouse + lastmile, ~5,000 orders/mo)
3. CONTEXT-trackflow-request-3.pdf (Invalid document - Incoming carrier rate pitch, not a client RFP)
"""

from __future__ import annotations

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUEST_1_LINES = [
    "SOLICITUD DE PROPUESTA (RFP) — OPERACIONES LOGÍSTICAS E-COMMERCE 2026",
    "Código de Referencia: RFP-MODAVIVA-2026-ES",
    "Empresa Solicitante (Cliente): ModaViva S.L.",
    "País de Origen y Operación: España (Spain) — Moneda de Cotización: EUR",
    "Sector: Moda y Textil E-Commerce (B2C / B2B)",
    "Fecha Límite de Entrega (Deadline): 2026-11-30",
    "Presupuesto de Referencia (Budget Range): 18.000 EUR - 24.000 EUR mensuales",
    "Volumen Estimado: 12.000 pedidos/mes",
    "",
    "1. RESUMEN Y ALCANCE DE LOS SERVICIOS SOLICITADOS",
    "ModaViva es una marca española de moda femenina y accesorios con sede en Madrid.",
    "Buscamos externalizar nuestra operación de almacenamiento (warehousing) y logística",
    "inversa (reverse logistics / gestión de devoluciones) en su centro logístico de Zaragoza.",
    "IMPORTANTE — ALCANCE EXCLUIDO DE ÚLTIMA MILLA:",
    "ModaViva NO solicita servicios de transporte de última milla (last mile). Contamos con",
    "un contrato corporativo directo con nuestro propio transportista para la distribución",
    "nacional y peninsular. Los paquetes preparados serán recogidos diariamente en el muelle",
    "de Zaragoza por nuestros vehículos concertados.",
    "",
    "2. REQUERIMIENTOS DE ALMACENAMIENTO (WAREHOUSE OPERATIONS)",
    "- Capacidad requerida: 450 pallets europeos y aproximadamente 1.800 SKUs activos de",
    "  prendas dobladas y colgadas (temporada otoño/invierno y primavera/verano).",
    "- Recepción de mercancía (inbound), control de calidad por muestreo y ubicación en rack.",
    "- Preparación de pedidos (picking y packing sostenible) para un volumen estimado de",
    "  12.000 pedidos/mes con corte de preparación a las 17:00 CET.",
    "- Indicar en la propuesta el costo por pallet/SKU, capacidad disponible en Zaragoza,",
    "  tiempo estimado de onboarding e integración WMS, y tabla de descuentos por volumen.",
    "",
    "3. REQUERIMIENTOS DE LOGÍSTICA INVERSA (REVERSE LOGISTICS)",
    "- Tasa media histórica de devoluciones en moda: 18% sobre pedidos enviados (~2.160",
    "  devoluciones mensuales recibidas en el almacén de Zaragoza).",
    "- Inspección de estado de prendas devueltas (etiquetado original, ausencia de manchas,",
    "  doblado, re-embolsado y reintegración automática de stock apto para la venta).",
    "- El procesamiento de devoluciones debe completarse respetando los estándares de calidad",
    "  (nunca prometiendo tiempos irreales menores a 48 horas, requerimos SLA estándar >= 48h).",
    "- Detallar costo unitario por devolución procesada y tiempos comprometidos de ciclo.",
]

REQUEST_2_LINES = [
    "From: operations@lunacosmetics-la.com",
    "To: miguel.torres@trackflow.com (Commercial Director - TrackFlow)",
    "Subject: Logistics Partnership Inquiry / RFP - Luna Cosmetics (US Warehousing + Last Mile)",
    "Date: October 15, 2026",
    "",
    "Hi Miguel and TrackFlow Commercial Team,",
    "",
    "We are Luna Cosmetics, a direct-to-consumer beauty and skincare brand based in",
    "Los Angeles, United States (Country: USA). We are scaling rapidly across the US market",
    "and would like to request a formal proposal (in USD) to outsource our fulfillment",
    "starting next month.",
    "",
    "Here are the key details of what we need from TrackFlow:",
    "- Client Name: Luna Cosmetics",
    "- Client Country: USA (Los Angeles operation, currency USD)",
    "- Services Requested: Warehousing (storage & pick/pack) + Last Mile delivery across the USA.",
    "- Note on Returns: We do NOT need reverse logistics / returns processing from TrackFlow",
    "  because opened cosmetic products cannot be restocked and we handle customer refunds",
    "  directly through our internal support team without physical return shipping.",
    "- Estimated Monthly Volume: ~5,000 pedidos/mes (5,000 orders/month).",
    "- Proposal Deadline: 2026-11-15",
    "- Target Budget Range: 25,000 USD - 32,000 USD per month",
    "",
    "Warehouse Operations Requirements (Los Angeles):",
    "We have 220 active cosmetic SKUs (serums, creams, and gift kits) requiring lot/expiry",
    "tracking and approximately 120 pallets of storage space in your Los Angeles facility.",
    "Please share your storage cost per pallet and per SKU, onboarding timeline, and volume",
    "discount tiers.",
    "",
    "Last Mile & Carrier Management Requirements (US Domestic):",
    "We ship approximately 5,000 B2C parcels per month across California (60%) and the rest",
    "of the continental United States (40%), average weight 0.8 lbs per parcel.",
    "Please provide your final shipping cost per order, available carriers by destination zone,",
    "and the on-time delivery SLA (%) that TrackFlow commits to achieving.",
    "",
    "Looking forward to your proposal!",
    "Best regards,",
    "Elena Vance — VP of Supply Chain, Luna Cosmetics (Los Angeles, USA)",
]

REQUEST_3_LINES = [
    "PROPUESTA COMERCIAL DE SERVICIOS DE TRANSPORTE PARA TRACKFLOW TECH",
    "Remitente: TransIberia & WestCoast Freight Carriers Corp.",
    "Destinatario: Departamento de Compras y Carrier Management — TrackFlow",
    "Asunto: Presentación de Tarifas Mayoristas de Flota FTL/LTL 2026 (Pitch de Proveedor)",
    "Fecha: 14 de Octubre de 2026",
    "",
    "Estimado equipo de compras de TrackFlow,",
    "",
    "Nos ponemos en contacto con ustedes como empresa transportista de carga pesada para",
    "ofrecerles nuestras nuevas tarifas mayoristas de transporte por carretera entre puertos",
    "marítimos y sus centros de distribución. Este documento es una oferta comercial entrante",
    "de nuestros servicios de flota para que TrackFlow nos contrate como proveedor externo.",
    "",
    "NO somos una marca de e-commerce ni estamos solicitando servicios de almacenamiento,",
    "preparación de pedidos ni logística inversa a TrackFlow. Por el contrario, buscamos",
    "convertirnos en uno de los transportistas subcontratados por TrackFlow.",
    "",
    "Resumen de nuestras tarifas de transporte de carga completa (FTL) para 2026:",
    "- Ruta Puerto de Valencia a Zaragoza: 680 EUR por camión completo de 33 pallets.",
    "- Ruta Puerto de Barcelona a Zaragoza: 620 EUR por camión completo de 33 pallets.",
    "- Ruta Long Beach Port a Los Ángeles: 490 USD por contenedor drayage de 40 pies.",
    "- Descuento del 8% para contrataciones superiores a 80 viajes mensuales.",
    "- Disponibilidad de flota diésel y eléctrica con seguimiento GPS básico.",
    "",
    "Quedamos a la espera de agendar una llamada de ventas con su director de transporte",
    "para dar de alta a TransIberia Freight como proveedor homologado en su ERP.",
    "Atentamente,",
    "Dirección Comercial — TransIberia & WestCoast Freight Carriers Corp.",
]


def write_pdf(target_path: Path, lines: list[str]) -> None:
    """Render a clean, multi-line text PDF using ReportLab."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(target_path), pagesize=A4)
    width, height = A4
    y = height - 2.2 * cm

    for idx, line in enumerate(lines):
        if y < 2.0 * cm:
            c.showPage()
            y = height - 2.2 * cm
        if idx == 0:
            c.setFont("Helvetica-Bold", 12)
        elif line.isupper() and len(line) > 5:
            c.setFont("Helvetica-Bold", 10)
        else:
            c.setFont("Helvetica", 10)
        c.drawString(2.0 * cm, y, line)
        y -= 0.55 * cm

    c.save()


def generate_all_seed_pdfs() -> list[Path]:
    """Generate the 3 seed PDFs in both rfp-requests/trackflow/ and docs/milestone-9/rfp-requests/trackflow/."""
    output_dirs = [
        PROJECT_ROOT / "rfp-requests" / "trackflow",
        PROJECT_ROOT / "docs" / "milestone-9" / "rfp-requests" / "trackflow",
    ]
    created_files: list[Path] = []
    specs = [
        ("CONTEXT-trackflow-request-1.pdf", REQUEST_1_LINES),
        ("CONTEXT-trackflow-request-2.pdf", REQUEST_2_LINES),
        ("CONTEXT-trackflow-request-3.pdf", REQUEST_3_LINES),
    ]
    for out_dir in output_dirs:
        for filename, lines in specs:
            pdf_path = out_dir / filename
            write_pdf(pdf_path, lines)
            created_files.append(pdf_path)
    return created_files


if __name__ == "__main__":
    paths = generate_all_seed_pdfs()
    for p in paths:
        print(f"Generated: {p}")
