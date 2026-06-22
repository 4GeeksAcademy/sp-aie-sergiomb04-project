export function Footer() {
  return (
    <footer role="contentinfo" className="border-t bg-white px-6 py-10">
      <div className="mx-auto grid max-w-6xl gap-8 text-center md:grid-cols-3 md:text-left">
        <div>
          <h2 className="text-xl font-bold text-blue-600">
            Track<span className="text-gray-800">Flow</span>
          </h2>
          <p className="mt-2 text-gray-600">
            Soluciones inteligentes de logistica de ultima milla para e-commerce.
          </p>
        </div>

        <div>
          <h3 className="mb-2 font-semibold text-gray-900">Contacto</h3>
          <p className="text-gray-600">
            <a href="mailto:info@trackflow.com">info@trackflow.com</a>
          </p>
          <p className="text-gray-600">
            <a href="tel:+12135550147">+1 (213) 555-0147</a>
          </p>
        </div>

        <div>
          <h3 className="mb-2 font-semibold text-gray-900">Ubicaciones</h3>
          <p className="text-gray-600">Los Angeles, USA</p>
          <p className="text-gray-600">Zaragoza, Espana</p>
        </div>
      </div>

      <div className="mt-10 text-center text-sm text-gray-500">
        © 2026 TrackFlow. Todos los derechos reservados.
      </div>
    </footer>
  );
}