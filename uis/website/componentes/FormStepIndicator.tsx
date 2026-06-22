type FormStepIndicatorProps = {
  currentStep: 1 | 2;
};

const steps = [
  { step: 1, label: "Paso 1: Empresa y contacto" },
  { step: 2, label: "Paso 2: Operacion y envio" },
] as const;

export function FormStepIndicator({ currentStep }: FormStepIndicatorProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 text-sm sm:flex-row"
      aria-label="Progreso del formulario"
    >
      {steps.map((item) => {
        const isCurrent = item.step === currentStep;

        return (
          <span
            key={item.step}
            aria-current={isCurrent ? "step" : undefined}
            className={[
              "rounded-full px-3 py-1",
              isCurrent ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-700",
            ].join(" ")}
          >
            {item.label}
          </span>
        );
      })}
    </div>
  );
}