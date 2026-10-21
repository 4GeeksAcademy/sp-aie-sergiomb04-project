import Link from "next/link";

export function Footer() {
  return (
    <footer role="contentinfo" className="border-t border-gray-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          {/* Brand info */}
          <div className="md:col-span-1">
            <Link href="/" className="flex items-center gap-1.5 text-2xl font-bold tracking-tight text-blue-600">
              <span>Track</span>
              <span className="text-gray-900 dark:text-white">Flow</span>
            </Link>
            <p className="mt-3 text-xs leading-relaxed text-gray-600 dark:text-slate-400">
              Plataforma tecnológica de logística de última milla, operaciones de almacén y devoluciones asistidas por IA para marcas de e-commerce transfronterizas.
            </p>
            <div className="mt-4 flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Sistemas Operativos 24/7 (LA & ZGZ)
            </div>
          </div>

          {/* Quick links */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">
              Navegación
            </h3>
            <ul className="mt-3 space-y-2 text-xs text-gray-600 dark:text-slate-400">
              <li>
                <a href="#servicios" className="hover:text-blue-600 dark:hover:text-blue-400 transition">
                  Servicios de Plataforma
                </a>
              </li>
              <li>
                <a href="#rastreo" className="hover:text-blue-600 dark:hover:text-blue-400 transition">
                  Seguimiento de Envíos
                </a>
              </li>
              <li>
                <a href="#operacion" className="hover:text-blue-600 dark:hover:text-blue-400 transition">
                  Flujo de Operación
                </a>
              </li>
              <li>
                <a href="#faq" className="hover:text-blue-600 dark:hover:text-blue-400 transition">
                  Preguntas Frecuentes
                </a>
              </li>
              <li>
                <Link href="/application" className="hover:text-blue-600 dark:hover:text-blue-400 transition">
                  Solicitar Propuesta de Servicio
                </Link>
              </li>
            </ul>
          </div>

          {/* Hubs & Coverage */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">
              Centros Operativos
            </h3>
            <ul className="mt-3 space-y-2.5 text-xs text-gray-600 dark:text-slate-400">
              <li>
                <strong className="block text-gray-900 dark:text-slate-200">Hub Los Ángeles (Whse LA-01)</strong>
                <span>California, USA · Conexión UPS, FedEx, DHL</span>
              </li>
              <li>
                <strong className="block text-gray-900 dark:text-slate-200">Hub Zaragoza (Plaza Logística)</strong>
                <span>Aragón, España · Conexión SEUR, MRW, DHL</span>
              </li>
            </ul>
          </div>

          {/* Contact & Systems */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">
              Contacto & Accesos
            </h3>
            <ul className="mt-3 space-y-2 text-xs text-gray-600 dark:text-slate-400">
              <li>
                <a href="mailto:info@trackflow.com" className="hover:text-blue-600 dark:hover:text-blue-400 transition">
                  info@trackflow.com
                </a>
              </li>
              <li>
                <a href="tel:+12135550147" className="hover:text-blue-600 dark:hover:text-blue-400 transition">
                  +1 (213) 555-0147
                </a>
              </li>
              <li className="pt-2">
                <a
                  href="http://localhost:3001"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 transition"
                >
                  <span>Acceso Portal Backoffice</span>
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-gray-100 pt-6 text-xs text-gray-500 sm:flex-row dark:border-slate-800 dark:text-slate-500">
          <p>© 2026 TrackFlow Tech. Todos los derechos reservados.</p>
          <div className="flex gap-6">
            <span className="hover:text-gray-700 dark:hover:text-slate-300 transition cursor-pointer">SLA Contractual &gt;90%</span>
            <span className="hover:text-gray-700 dark:hover:text-slate-300 transition cursor-pointer">Política de Privacidad</span>
            <span className="hover:text-gray-700 dark:hover:text-slate-300 transition cursor-pointer">Términos de Servicio</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
