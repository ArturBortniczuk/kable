document.addEventListener('DOMContentLoaded', function() {
    // Obsługa przycisków "Brak dostępności" i "Czekamy na oferty"
    document.querySelectorAll('.no-availability-btn, .waiting-offers-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault(); // Zapobiegaj domyślnej akcji przycisku

            const card = this.closest('.card');
            const cardBody = card.querySelector('.card-body');
            const responseFields = card.querySelector('.response-fields');
            const priceInputs = card.querySelectorAll('input[type="number"]');
            const radioInputs = card.querySelectorAll('input[type="radio"]');
            const commentsField = card.querySelector('textarea[name*="comments"]');
            const isNoAvailability = this.classList.contains('no-availability-btn');

            // Dezaktywuj wszystkie pola
            priceInputs.forEach(input => {
                input.value = '';
                input.disabled = true;
                input.closest('.form-group').style.display = 'none';
            });

            radioInputs.forEach(input => {
                input.checked = false;
                input.disabled = true;
            });

            responseFields.style.display = 'none';

            // Ustaw odpowiedni tekst w polu komentarzy
            commentsField.value = isNoAvailability ? 'Brak dostępności' : 'Czekamy na oferty';
            commentsField.closest('.form-group').style.display = 'block';

            // Włącz z powrotem po kliknięciu w pole komentarza
            commentsField.addEventListener('focus', function() {
                if (this.value === 'Brak dostępności' || this.value === 'Czekamy na oferty') {
                    this.value = '';
                }
            });

            // Zaznacz przycisk jako aktywny
            button.classList.add('active');
            const otherButton = button.classList.contains('no-availability-btn')
                ? button.nextElementSibling
                : button.previousElementSibling;
            otherButton.classList.remove('active');
        });
    });

    // Obsługa własnej daty dostawy
    document.querySelectorAll('.delivery-option').forEach(radio => {
        radio.addEventListener('change', function() {
            const customDeliveryDateDiv = this.closest('.form-group').querySelector('.custom-delivery-date');
            const customDateInput = customDeliveryDateDiv.querySelector('input');

            if (this.value === 'custom') {
                customDeliveryDateDiv.style.display = 'block';
                customDateInput.required = true;
            } else {
                customDeliveryDateDiv.style.display = 'none';
                customDateInput.required = false;
                customDateInput.value = '';
            }
        });
    });

    // Obsługa własnej daty ważności
    document.querySelectorAll('.validity-option').forEach(radio => {
        radio.addEventListener('change', function() {
            const customDateInput = this.closest('.form-group').querySelector('.custom-validity-date');
            if (this.value === 'custom') {
                customDateInput.style.display = 'block';
                customDateInput.required = true;
            } else {
                customDateInput.style.display = 'none';
                customDateInput.required = false;
                customDateInput.value = '';
            }
        });
    });
});