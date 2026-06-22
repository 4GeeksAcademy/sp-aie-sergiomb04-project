import type { Metadata } from "next";

import { Features, type FeatureItem } from "../componentes/Features";
import { Hero, type HeroStat } from "../componentes/Hero";

const heroStats: HeroStat[] = [
  { value: "130+", label: "Empleados" },
  { value: "2", label: "Paises" },
  { value: "9M€", label: "Facturacion" },
  { value: "8", label: "Transportistas" },
];

const featureItems: FeatureItem[] = [
  {
    title: "📦 Gestion de inventario en tiempo real",
    description:
      "Visualiza el stock de todos tus almacenes en una sola plataforma con datos actualizados al instante.",
  },
  {
    title: "🚚 Seleccion inteligente de transportistas",
    description:
      "Algoritmos que eligen automaticamente el mejor transportista segun coste, tiempo y destino.",
  },
  {
    title: "📊 Dashboard unificado",
    description:
      "KPIs en tiempo real sobre envios, entregas, devoluciones y rendimiento operativo.",
  },
  {
    title: "🤖 Automatizacion con IA",
    description:
      "Procesamiento automatico de pedidos, clasificacion de devoluciones y atencion al cliente inteligente.",
  },
  {
    title: "🔄 Gestion de devoluciones",
    description:
      "Flujos automatizados para aprobar, recoger y procesar devoluciones sin intervencion manual.",
  },
  {
    title: "🌐 Tracking unificado",
    description:
      "Consulta el estado de cualquier envio desde una sola interfaz, sin importar el transportista.",
  },
];

const benefitItems: FeatureItem[] = [
  {
    title: "⚡ Ahorro de tiempo",
    description:
      "Automatiza tareas repetitivas y reduce horas de trabajo manual en operaciones y soporte.",
  },
  {
    title: "📉 Reduccion de errores",
    description:
      "Minimiza fallos humanos con sistemas inteligentes y procesos estandarizados.",
  },
  {
    title: "📦 Escalabilidad",
    description:
      "Crece sin fricciones operativas, gestionando mas pedidos sin aumentar costes proporcionalmente.",
  },
  {
    title: "😊 Mejor experiencia del cliente",
    description:
      "Seguimiento en tiempo real y respuestas rapidas que aumentan la satisfaccion del usuario final.",
  },
  {
    title: "🌍 Operacion global",
    description:
      "Gestiona multiples paises, almacenes y transportistas desde una unica plataforma.",
  },
  {
    title: "📊 Decisiones basadas en datos",
    description:
      "Accede a metricas clave en tiempo real para tomar decisiones estrategicas con confianza.",
  },
];

export const metadata: Metadata = {
  title: "Inicio",
  description:
    "Soluciones inteligentes de logistica de ultima milla para e-commerce.",
};

export default function Home() {
  return (
    <main id="main-content" role="main">
      <Hero stats={heroStats} />

      <Features
        headingId="features-title"
        title="Caracteristicas principales"
        description="Una plataforma disenada para automatizar y escalar cada parte de tu operacion logistica."
        items={featureItems}
        backgroundClassName="bg-white"
        borderedCards
      />

      <Features
        headingId="benefits-title"
        title="Por que elegir TrackFlow?"
        description="Mas eficiencia, menos errores y una mejor experiencia para tus clientes."
        items={benefitItems}
        backgroundClassName="bg-gray-100"
      />
    </main>
  );
}
