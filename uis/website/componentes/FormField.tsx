import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

type BaseFieldProps = {
  id: string;
  label: string;
  required?: boolean;
  error?: string;
};

type InputFieldProps = BaseFieldProps & {
  as?: "input";
  inputProps?: InputHTMLAttributes<HTMLInputElement>;
};

type SelectOption = {
  label: string;
  value: string;
};

type SelectFieldProps = BaseFieldProps & {
  as: "select";
  selectProps?: SelectHTMLAttributes<HTMLSelectElement>;
  options: SelectOption[];
};

type TextareaFieldProps = BaseFieldProps & {
  as: "textarea";
  textareaProps?: TextareaHTMLAttributes<HTMLTextAreaElement>;
};

type FormFieldProps = InputFieldProps | SelectFieldProps | TextareaFieldProps;

const baseControlClassName =
  "mt-1 w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500";

export function FormField(props: FormFieldProps) {
  const { id, label, required = false, error } = props;
  const describedBy = error ? `${id}-error` : undefined;
  const controlClassName = `${baseControlClassName} ${error ? "border-red-500" : "border-gray-300"}`;

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label}
        {required ? " *" : ""}
      </label>

      {props.as === "select" ? (
        <select
          id={id}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={controlClassName}
          {...props.selectProps}
        >
          {props.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : null}

      {props.as === "textarea" ? (
        <textarea
          id={id}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={controlClassName}
          {...props.textareaProps}
        />
      ) : null}

      {props.as === undefined || props.as === "input" ? (
        <input
          id={id}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={controlClassName}
          {...props.inputProps}
        />
      ) : null}

      {error ? (
        <p id={`${id}-error`} role="alert" className="mt-1 text-sm text-red-500">
          {error}
        </p>
      ) : null}
    </div>
  );
}