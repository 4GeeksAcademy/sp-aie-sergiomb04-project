"use client";

import { useState } from "react";

import { FormField } from "./FormField";
import { FormStepIndicator } from "./FormStepIndicator";

type FormValues = {
  company: string;
  industry: string;
  country: string;
  name: string;
  email: string;
  phone: string;
  volume: string;
  warehouses: string;
  services: string;
  message: string;
};

type FormErrors = Partial<Record<keyof FormValues, string>>;

type StatusMessage = {
  tone: "success" | "error";
  text: string;
} | null;

const initialValues: FormValues = {
  company: "",
  industry: "",
  country: "",
  name: "",
  email: "",
  phone: "",
  volume: "",
  warehouses: "",
  services: "Gestion de almacen",
  message: "",
};

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateStep1(values: FormValues) {
  const errors: FormErrors = {};

  if (!values.company.trim()) {
    errors.company = "Este campo es obligatorio";
  }

  if (values.name.trim().length < 3) {
    errors.name = "Minimo 3 caracteres";
  }

  if (!values.country.trim()) {
    errors.country = "Este campo es obligatorio";
  }

  if (!emailRegex.test(values.email)) {
    errors.email = "Email no valido";
  }

  return errors;
}

function validateStep2(values: FormValues) {
  const errors: FormErrors = {};

  if (!values.volume || Number(values.volume) <= 0) {
    errors.volume = "Introduce un numero valido";
  }

  return errors;
}

export function ServiceApplicationForm() {
  const [currentStep, setCurrentStep] = useState<1 | 2>(1);
  const [values, setValues] = useState<FormValues>(initialValues);
  const [errors, setErrors] = useState<FormErrors>({});
  const [statusMessage, setStatusMessage] = useState<StatusMessage>(null);

  function updateField<K extends keyof FormValues>(field: K, value: FormValues[K]) {
    setValues((currentValues) => ({ ...currentValues, [field]: value }));
    setErrors((currentErrors) => ({ ...currentErrors, [field]: undefined }));
  }

  function handleNextStep() {
    const nextErrors = validateStep1(values);

    if (Object.keys(nextErrors).length > 0) {
      setErrors((currentErrors) => ({ ...currentErrors, ...nextErrors }));
      setStatusMessage({
        tone: "error",
        text: "Completa correctamente los campos obligatorios del paso 1.",
      });
      return;
    }

    setStatusMessage(null);
    setCurrentStep(2);
  }

  function handlePreviousStep() {
    setStatusMessage(null);
    setCurrentStep(1);
  }

  function handleReset() {
    setValues(initialValues);
    setErrors({});
    setStatusMessage(null);
    setCurrentStep(1);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors = {
      ...validateStep1(values),
      ...validateStep2(values),
    };

    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      setStatusMessage({
        tone: "error",
        text: "Revisa los campos marcados en rojo antes de enviar.",
      });

      if (nextErrors.company || nextErrors.name || nextErrors.email || nextErrors.country) {
        setCurrentStep(1);
      } else {
        setCurrentStep(2);
      }

      return;
    }

    setStatusMessage({
      tone: "success",
      text: "Enviado correctamente (simulacion)",
    });
    setValues(initialValues);
    setErrors({});
    setCurrentStep(1);
  }

  return (
    <form
      className="space-y-8"
      aria-labelledby="form-title"
      aria-describedby="form-description required-note"
      noValidate
      onSubmit={handleSubmit}
      onReset={handleReset}
    >
      <p
        id="form-status"
        className={[
          "mt-2 text-center text-sm font-medium",
          statusMessage ? "block" : "hidden",
          statusMessage?.tone === "success" ? "text-green-500" : "text-red-500",
        ].join(" ")}
        role="status"
        aria-live="polite"
      >
        {statusMessage?.text}
      </p>

      <FormStepIndicator currentStep={currentStep} />

      <section
        id="step-1"
        data-step="1"
        aria-labelledby="step-1-title"
        className={currentStep === 1 ? "space-y-8" : "hidden"}
        hidden={currentStep !== 1}
      >
        <fieldset className="space-y-4">
          <legend id="step-1-title" className="text-lg font-semibold text-gray-900">
            Informacion de la empresa
          </legend>

          <FormField
            id="company"
            label="Nombre de la empresa"
            required
            error={errors.company}
            inputProps={{
              name: "company",
              type: "text",
              autoComplete: "organization",
              value: values.company,
              onChange: (event) => updateField("company", event.target.value),
            }}
          />

          <FormField
            id="industry"
            label="Sector"
            inputProps={{
              name: "industry",
              type: "text",
              placeholder: "Ej: E-commerce, Retail...",
              value: values.industry,
              onChange: (event) => updateField("industry", event.target.value),
            }}
          />

          <FormField
            id="country"
            label="Pais de operacion"
            required
            error={errors.country}
            as="select"
            selectProps={{
              name: "country",
              autoComplete: "country-name",
              value: values.country,
              onChange: (event) => updateField("country", event.target.value),
            }}
            options={[
              { label: "Selecciona una opcion", value: "" },
              { label: "Estados Unidos", value: "Estados Unidos" },
              { label: "Espana", value: "Espana" },
              { label: "Otro", value: "Otro" },
            ]}
          />
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="text-lg font-semibold text-gray-900">
            Informacion de contacto
          </legend>

          <FormField
            id="name"
            label="Nombre completo"
            required
            error={errors.name}
            inputProps={{
              name: "name",
              type: "text",
              autoComplete: "name",
              value: values.name,
              onChange: (event) => updateField("name", event.target.value),
            }}
          />

          <div className="grid gap-4 md:grid-cols-2">
            <FormField
              id="email"
              label="Email"
              required
              error={errors.email}
              inputProps={{
                name: "email",
                type: "email",
                autoComplete: "email",
                value: values.email,
                onChange: (event) => updateField("email", event.target.value),
              }}
            />

            <FormField
              id="phone"
              label="Telefono"
              inputProps={{
                name: "phone",
                type: "tel",
                autoComplete: "tel",
                value: values.phone,
                onChange: (event) => updateField("phone", event.target.value),
              }}
            />
          </div>
        </fieldset>

        <div className="text-center">
          <button
            id="next-step"
            type="button"
            onClick={handleNextStep}
            className="w-full rounded-lg bg-blue-600 px-8 py-3 font-medium text-white transition hover:bg-blue-700 md:w-auto"
          >
            Continuar al paso 2
          </button>
        </div>
      </section>

      <section
        id="step-2"
        data-step="2"
        aria-labelledby="step-2-title"
        className={currentStep === 2 ? "space-y-8" : "hidden"}
        hidden={currentStep !== 2}
      >
        <fieldset className="space-y-4">
          <legend id="step-2-title" className="text-lg font-semibold text-gray-900">
            Operacion logistica
          </legend>

          <FormField
            id="volume"
            label="Volumen mensual de pedidos"
            required
            error={errors.volume}
            inputProps={{
              name: "volume",
              type: "number",
              min: 0,
              placeholder: "Ej: 5000",
              value: values.volume,
              onChange: (event) => updateField("volume", event.target.value),
            }}
          />

          <FormField
            id="warehouses"
            label="Numero de almacenes"
            inputProps={{
              name: "warehouses",
              type: "number",
              min: 1,
              value: values.warehouses,
              onChange: (event) => updateField("warehouses", event.target.value),
            }}
          />

          <FormField
            id="services"
            label="Servicios de interes"
            as="select"
            selectProps={{
              name: "services",
              value: values.services,
              onChange: (event) => updateField("services", event.target.value),
            }}
            options={[
              { label: "Gestion de almacen", value: "Gestion de almacen" },
              { label: "Envios ultima milla", value: "Envios ultima milla" },
              { label: "Logistica inversa", value: "Logistica inversa" },
              { label: "Solucion completa", value: "Solucion completa" },
            ]}
          />
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="text-lg font-semibold text-gray-900">
            Detalles adicionales
          </legend>

          <FormField
            id="message"
            label="Cuentanos mas sobre tu operacion"
            as="textarea"
            textareaProps={{
              name: "message",
              rows: 4,
              placeholder: "Describe tus necesidades logisticas...",
              value: values.message,
              onChange: (event) => updateField("message", event.target.value),
            }}
          />
        </fieldset>

        <div className="text-center">
          <button
            id="prev-step"
            type="button"
            onClick={handlePreviousStep}
            className="w-full rounded-lg border border-gray-300 bg-white px-8 py-3 font-medium transition hover:bg-gray-50 md:w-auto"
          >
            Volver al paso 1
          </button>

          <button
            type="submit"
            className="mt-2 w-full rounded-lg bg-blue-600 px-8 py-3 font-medium text-white transition hover:bg-blue-700 md:mt-0 md:ml-2 md:w-auto"
          >
            Enviar solicitud
          </button>

          <button
            type="reset"
            className="mt-2 w-full rounded-lg bg-gray-500 px-8 py-3 font-medium text-white transition hover:bg-gray-600 md:mt-0 md:ml-2 md:w-auto"
          >
            Restablecer
          </button>
        </div>
      </section>
    </form>
  );
}