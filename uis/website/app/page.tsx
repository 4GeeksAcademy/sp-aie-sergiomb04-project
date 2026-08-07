import type { Metadata } from "next";

import { Features, type FeatureItem } from "../componentes/Features";
import { Hero, type HeroStat } from "../componentes/Hero";

const heroStats: HeroStat[] = [
  { value: "130+", label: "Empleados" },
  { value: "2", label: "Países" },
  { value: "9M€", label: "Facturación" },
  { value: "8", label: "Transportistas" },
];

const featureItems: FeatureItem[] = [
  {
    title: "📦 Gestión de inventario en tiempo real",
    description:
      "Visualiza el stock de todos tus almacenes en una sola plataforma con datos actualizados al instante.",
  },
  {
    title: "🚚 Selección inteligente de transportistas",
    description:
      "Algoritmos que eligen automáticamente el mejor transportista según coste, tiempo y destino.",
  },
  {
    title: "📊 Dashboard unificado",
    description:
      "KPIs en tiempo real sobre envíos, entregas, devoluciones y rendimiento operativo.",
  },
  {
    title: "🤖 Automatización con IA",
    description:
      "Procesamiento automático de pedidos, clasificación de devoluciones y atención al cliente inteligente.",
  },
  {
    title: "🔄 Gestión de devoluciones",
    description:
      "Flujos automatizados para aprobar, recoger y procesar devoluciones sin intervención manual.",
  },
  {
    title: "🌐 Tracking unificado",
    description:
      "Consulta el estado de cualquier envío desde una sola interfaz, sin importar el transportista.",
  },
];

const benefitItems: FeatureItem[] = [
  {
    title: "⚡ Ahorro de tiempo",
    description:
      "Automatiza tareas repetitivas y reduce horas de trabajo manual en operaciones y soporte.",
  },
  {
    title: "📉 Reducción de errores",
    description:
      "Minimiza fallos humanos con sistemas inteligentes y procesos estandarizados.",
  },
  {
    title: "📦 Escalabilidad",
    description:
      "Crece sin fricciones operativas, gestionando más pedidos sin aumentar costes proporcionalmente.",
  },
  {
    title: "😊 Mejor experiencia del cliente",
    description:
      "Seguimiento en tiempo real y respuestas rápidas que aumentan la satisfacción del usuario final.",
  },
  {
    title: "🌍 Operación global",
    description:
      "Gestiona múltiples países, almacenes y transportistas desde una única plataforma.",
  },
  {
    title: "📊 Decisiones basadas en datos",
    description:
      "Accede a métricas clave en tiempo real para tomar decisiones estratégicas con confianza.",
  },
];

export const metadata: Metadata = {
  title: "Inicio",
  description:
    "Soluciones inteligentes de logística de última milla para e-commerce.",
};

export default function Home() {
  return (
    <main id="main-content" role="main">
      <Hero stats={heroStats} />

      <Features
        headingId="features-title"
        title="Características principales"
        description="Una plataforma diseñada para automatizar y escalar cada parte de tu operación logística."
        items={featureItems}
        backgroundClassName="bg-white"
        borderedCards
      />

      <Features
        headingId="benefits-title"
        title="Por qué elegir TrackFlow?"
        description="Más eficiencia, menos errores y una mejor experiencia para tus clientes."
        items={benefitItems}
        backgroundClassName="bg-gray-100"
      />
    </main>
  );
}
