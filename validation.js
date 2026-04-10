// Espera a que el DOM esté listo
document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector("form");
    const formStatus = document.getElementById("form-status");

    // Inputs
    const company = document.getElementById("company");
    const name = document.getElementById("name");
    const email = document.getElementById("email");
    const volume = document.getElementById("volume");

    // Regex simple para email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    // Función para mostrar error visual
    function showError(input, message) {
        input.classList.add("border-red-500");
        input.classList.remove("border-gray-300");
        input.setAttribute("aria-invalid", "true");

        const errorId = `${input.id}-error`;
        const currentDescribedBy = input.getAttribute("aria-describedby") || "";
        if (!currentDescribedBy.split(" ").includes(errorId)) {
            input.setAttribute("aria-describedby", `${currentDescribedBy} ${errorId}`.trim());
        }

        // Si ya existe mensaje, no duplicar
        if (!input.nextElementSibling || !input.nextElementSibling.classList.contains("error-msg")) {
            const error = document.createElement("p");
            error.textContent = message;
            error.id = errorId;
            error.setAttribute("role", "alert");
            error.classList.add("text-red-500", "text-sm", "mt-1", "error-msg");
            input.parentNode.appendChild(error);
        }
    }

    // Función para limpiar error
    function clearError(input) {
        input.classList.remove("border-red-500");
        input.removeAttribute("aria-invalid");

        const errorId = `${input.id}-error`;
        const currentDescribedBy = (input.getAttribute("aria-describedby") || "")
            .split(" ")
            .filter((id) => id && id !== errorId)
            .join(" ");

        if (currentDescribedBy) {
            input.setAttribute("aria-describedby", currentDescribedBy);
        } else {
            input.removeAttribute("aria-describedby");
        }

        const error = input.parentNode.querySelector(".error-msg");
        if (error) error.remove();
    }

    // Validaciones individuales
    function validateCompany() {
        if (company.value.trim() === "") {
            showError(company, "Este campo es obligatorio");
            return false;
        }
        clearError(company);
        return true;
    }

    function validateName() {
        if (name.value.trim().length < 3) {
            showError(name, "Mínimo 3 caracteres");
            return false;
        }
        clearError(name);
        return true;
    }

    function validateEmail() {
        if (!emailRegex.test(email.value)) {
            showError(email, "Email no válido");
            return false;
        }
        clearError(email);
        return true;
    }

    function validateVolume() {
        if (volume.value === "" || Number(volume.value) <= 0) {
            showError(volume, "Introduce un número válido");
            return false;
        }
        clearError(volume);
        return true;
    }

    // Validación en tiempo real (UX mejor)
    company.addEventListener("input", validateCompany);
    name.addEventListener("input", validateName);
    email.addEventListener("input", validateEmail);
    volume.addEventListener("input", validateVolume);

    // Validación al enviar formulario
    form.addEventListener("submit", (e) => {
        e.preventDefault(); // Siempre prevenimos el envío real

        const isValid =
            validateCompany() &&
            validateName() &&
            validateEmail() &&
            validateVolume();

        if (!isValid) {
            if (formStatus) {
                formStatus.classList.remove("hidden");
                formStatus.textContent = "Revisa los campos marcados en rojo antes de enviar.";
                formStatus.classList.add("text-red-500");
                formStatus.classList.remove("text-green-500");
            }
            return;
        }

        // Simulación de envío exitoso
        if (formStatus) {
            formStatus.classList.remove("hidden");
            formStatus.textContent = "Enviado correctamente ✅ (simulación)";
            formStatus.classList.add("text-green-500");
            formStatus.classList.remove("text-red-500");
        }

        // Opcional: limpiar formulario
        form.reset();

        // Opcional: limpiar estados visuales
        [company, name, email, volume].forEach(input => clearError(input));
    });

});