import type { Metadata } from "next";

import { Features, type FeatureItem } from "../componentes/Features";
import { Hero, type HeroStat } from "../componentes/Hero";
import { TrackingWidget } from "../componentes/TrackingWidget";
import { OperationalWorkflow } from "../componentes/OperationalWorkflow";
import { FaqSection } from "../componentes/FaqSection";
import { CtaBanner } from "../componentes/CtaBanner";

const heroStats: HeroStat[] = [
  { value: "130+", label: "Especialistas", sublabel: "Equipo logístico y tech" },
  { value: "2 Hubs", label: "Los Ángeles & Zaragoza", sublabel: "Operativa transfronteriza" },
  { value: "98.5%", label: "SLA de Entrega", sublabel: "Compromiso contractual >90%" },
  { value: "8", label: "Carriers Integrados", sublabel: "UPS, FedEx, DHL, SEUR, MRW" },
];

const featureItems: FeatureItem[] = [
  {
    title: "📦 Gestión de inventario en tiempo real",
    description:
      "Visualiza el stock de tus almacenes en Los Ángeles y Zaragoza en una sola plataforma con datos sincronizados por SKU y alertas preventivas.",
  },
  {
    title: "🚚 Smart Carrier Dispatcher con IA",
    description:
      "Algoritmos que eligen automáticamente el transportista óptimo según peso, coste, plazo de entrega y destino sin requerir asignación manual.",
  },
  {
    title: "📊 Dashboard de telemetría y KPIs",
    description:
      "Métricas operacionales en tiempo real sobre rendimiento de almacén, tiempos de tránsito, tasa de discrepancia y cumplimiento de SLAs.",
  },
  {
    title: "🤖 Asistente de operaciones y RAG",
    description:
      "Automatización de consultas operativas y soporte al cliente conectado directamente a la base de conocimiento oficial de TrackFlow.",
  },
  {
    title: "🔄 Devoluciones automatizadas en <48h",
    description:
      "Flujos de inspección y aprobación automática de devoluciones con análisis asistido por imagen para acelerar reembolsos y reventas.",
  },
  {
    title: "🌐 Tracking unificado multicarrier",
    description:
      "Consulta y comparte el estado de cualquier paquete desde una sola interfaz, unificando eventos de UPS, FedEx, DHL, SEUR y MRW.",
  },
];

const benefitItems: FeatureItem[] = [
  {
    title: "⚡ Ahorro de horas operativas",
    description:
      "Automatiza el enrutamiento y empaquetado de pedidos, eliminando hojas de cálculo y comunicaciones fragmentadas.",
  },
  {
    title: "📉 Reducción drástica de incidencias",
    description:
      "Previene roturas de stock y errores de etiquetado mediante validaciones automáticas antes del despacho a transportista.",
  },
  {
    title: "📦 Escalabilidad para picos estacionales",
    description:
      "Soporta incrementos de volumen en Black Friday y campañas promocionales sin degradar la calidad del servicio ni los tiempos de entrega.",
  },
  {
    title: "😊 Experiencia de cliente transparente",
    description:
      "Tus compradores reciben notificaciones precisas y disfrutan de un portal de devoluciones ágil y sin fricciones.",
  },
  {
    title: "🌍 Cobertura internacional consolidada",
    description:
      "Gestiona tus ventas en Estados Unidos y Europa desde una infraestructura centralizada con tarifas y contratos unificados.",
  },
  {
    title: "📊 Decisiones con datos verificables",
    description:
      "Informes semanales automatizados y visibilidad de costes por almacén para optimizar tus márgenes de distribución.",
  },
];

export const metadata: Metadata = {
  title: "Inicio | Logística Inteligente para E-Commerce",
  description:
    "Plataforma tecnológica de última milla, almacenamiento y devoluciones automatizadas con IA en EE. UU. y España.",
};

export default function Home() {
  return (
    <main id="main-content" role="main">
      <Hero stats={heroStats} />

      <Features
        sectionId="servicios"
        headingId="features-title"
        title="Capacidades de la Plataforma"
        description="Una arquitectura diseñada para automatizar, unificar y escalar cada fase de tu operativa logística."
        items={featureItems}
        backgroundClassName="bg-white dark:bg-slate-900"
        borderedCards
      />

      {/* Widget de Rastreo Demostrativo (Bloque 2) */}
      <TrackingWidget />

      {/* Flujo Operativo de Extremo a Extremo (Bloque 3) */}
      <OperationalWorkflow />

      {/* Beneficios & Razones */}
      <Features
        headingId="benefits-title"
        title="¿Por qué confiar en TrackFlow Tech?"
        description="Eficiencia contrastada, menos incidencias operativas y un control total de tu cadena de suministro."
        items={benefitItems}
        backgroundClassName="bg-white dark:bg-slate-900"
        borderedCards
      />

      {/* Preguntas Frecuentes / Base de Conocimiento (Relleno y Confianza) */}
      <FaqSection />

      {/* Banner de Acción Pre-Footer */}
      <CtaBanner />
    </main>
  );
}
