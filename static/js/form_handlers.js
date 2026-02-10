document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicjalizacja formularza...');
    initializeAllHandlers();
});

function initializeAllHandlers() {
    // Inicjalizacja wszystkich handlerów
    console.log('Inicjalizacja handlerów...');
    handleVoltageFields();
    handlePackagingFields();
    initializeAddCableButton();
}

// Obsługa pól napięcia dla kabli
function handleVoltageFields() {
    document.querySelectorAll('.cable-form').forEach((cableForm, formIndex) => {
        const cableTypeInput = cableForm.querySelector('.cable-type-input');
        const voltageButtons = cableForm.querySelector('.voltage-buttons');
        const commentsField = cableForm.querySelector('.comments-field');

        // Usuń stare listenery
        cableTypeInput.removeEventListener('input', cableTypeInput.inputHandler);

        // Zdefiniuj nowy handler
        cableTypeInput.inputHandler = function() {
            const value = this.value.toUpperCase();
            console.log(`Form ${formIndex} cable type:`, value);

            if (value.includes('XRU') || value.includes('XNRU')) {
                console.log(`Showing voltage buttons for form ${formIndex}`);
                voltageButtons.style.display = 'block';

                voltageButtons.querySelectorAll('input[type="radio"]').forEach(radio => {
                    console.log(`Radio button details for form ${formIndex}:`, {
                        name: radio.name,
                        id: radio.id,
                        value: radio.value
                    });

                    // Usuń stare listenery
                    radio.removeEventListener('change', radio.changeHandler);

                    // Zdefiniuj nowy handler
                    radio.changeHandler = function() {
                        console.log(`Radio button changed in form ${formIndex}:`, {
                            name: this.name,
                            value: this.value
                        });

                        const textarea = commentsField.querySelector('textarea');
                        textarea.required = this.value === 'other';
                        textarea.placeholder = this.value === 'other'
                            ? 'Podaj wartość napięcia (wymagane)'
                            : 'Uwagi do kabla (opcjonalnie)';

                        if (!textarea.required) {
                            textarea.value = '';
                        }
                    };

                    radio.addEventListener('change', radio.changeHandler);
                });
            } else {
                console.log(`Hiding voltage buttons for form ${formIndex}`);
                voltageButtons.style.display = 'none';
                voltageButtons.querySelectorAll('input[type="radio"]').forEach(radio => {
                    radio.checked = false;
                });
            }
        };

        // Dodaj nowy listener
        cableTypeInput.addEventListener('input', cableTypeInput.inputHandler);

        // Wywołaj event input, aby ustawić początkowy stan
        cableTypeInput.dispatchEvent(new Event('input'));
    });
}

function updateVoltageVisibility(input) {
    const cableForm = input.closest('.cable-form');
    const voltageButtons = cableForm.querySelector('.voltage-buttons');
    const commentsField = cableForm.querySelector('.comments-field');
    const value = input.value.toUpperCase();

    console.log('Sprawdzanie typu kabla:', value);

    if (value.includes('XRU') || value.includes('XNRU')) {
        console.log('Znaleziono kabel XRU/XNRU');
        voltageButtons.style.display = 'block';

        voltageButtons.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.required = true;

            // Dodaj listener dla każdego radio buttona
            radio.addEventListener('change', function() {
                const textarea = commentsField.querySelector('textarea');
                textarea.required = this.value === 'other';
                if (!textarea.required) {
                    textarea.value = '';
                }
            });
        });
    } else {
        console.log('Inny typ kabla');
        voltageButtons.style.display = 'none';
        voltageButtons.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.required = false;
            radio.checked = false;
        });
        if (commentsField) {
            const textarea = commentsField.querySelector('textarea');
            textarea.required = false;
            textarea.value = '';
        }
    }
}

// Obsługa pól dla konfekcji i dokładnych odcinków
function handlePackagingFields() {
    document.querySelectorAll('select[name*="packaging"]').forEach(select => {
        const cableForm = select.closest('.cable-form');
        const specificLengthsField = cableForm.querySelector('.specific-lengths-field');
        const specificLengthsTextarea = cableForm.querySelector('textarea[name*="specific_lengths"]');

        // Sprawdź początkowy stan
        if (select.value === 'dokładne odcinki' && specificLengthsTextarea.value) {
            initializeSpecificLengths(cableForm, specificLengthsTextarea.value);
        }

        select.addEventListener('change', function() {
            console.log('Zmiana typu konfekcji:', this.value);
            const cableForm = this.closest('.cable-form');
            const specificLengthsField = cableForm.querySelector('.specific-lengths-field');
            const lengthInput = cableForm.querySelector('input[name*="length"]');

            if (this.value === 'dokładne odcinki') {
                console.log('Wybrano dokładne odcinki');
                specificLengthsField.style.display = 'block';
                lengthInput.readOnly = true;

                let sectionsContainer = specificLengthsField.querySelector('.length-sections-container');
                if (!sectionsContainer || sectionsContainer.children.length === 0) {
                    if (!sectionsContainer) {
                        sectionsContainer = document.createElement('div');
                        sectionsContainer.className = 'length-sections-container mb-3';
                        specificLengthsField.insertBefore(sectionsContainer, specificLengthsField.querySelector('button'));
                    }
                    addLengthSection(sectionsContainer);
                }
            } else {
                console.log('Wybrano standardową konfekcję');
                specificLengthsField.style.display = 'none';
                lengthInput.readOnly = false;
                lengthInput.value = '';
                const textarea = specificLengthsField.querySelector('textarea');
                if (textarea) textarea.value = '';
            }
        });
    });

    // Dodaj obsługę przycisków dodawania odcinków
    document.querySelectorAll('button[onclick*="addLengthSection"]').forEach(button => {
        button.onclick = function() {
            const container = this.previousElementSibling;
            addLengthSection(container);
        };
    });
}

function addLengthSection(container) {
    console.log('Dodawanie sekcji długości');
    const section = document.createElement('div');
    section.className = 'length-section d-flex gap-2 align-items-center mb-2';

    // Pole długości
    const lengthInput = document.createElement('input');
    lengthInput.type = 'number';
    lengthInput.className = 'form-control form-control-sm length-value';
    lengthInput.placeholder = 'Długość odcinka (m)';
    lengthInput.min = '1';
    lengthInput.required = true;

    // Pole ilości
    const quantityInput = document.createElement('input');
    quantityInput.type = 'number';
    quantityInput.className = 'form-control form-control-sm length-quantity';
    quantityInput.placeholder = 'Ilość odcinków';
    quantityInput.min = '1';
    quantityInput.required = true;

    section.appendChild(lengthInput);
    section.appendChild(quantityInput);

    // Dodaj przycisk usuwania (oprócz pierwszej sekcji)
    if (container.children.length > 0) {
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'btn btn-danger btn-sm ms-2';
        removeButton.innerHTML = '×';
        removeButton.onclick = () => {
            section.remove();
            updateTotalLength(container);
        };
        section.appendChild(removeButton);
    }

    container.appendChild(section);

    // Dodaj listenery
    [lengthInput, quantityInput].forEach(input => {
        input.addEventListener('input', () => updateTotalLength(container));
    });
}

function updateTotalLength(container) {
    console.log('Aktualizacja całkowitej długości');
    const cableForm = container.closest('.cable-form');
    const totalLengthInput = cableForm.querySelector('input[name*="length"]');
    const textarea = cableForm.querySelector('textarea[name*="specific_lengths"]');

    let totalLength = 0;
    const sections = [];

    container.querySelectorAll('.length-section').forEach(section => {
        const length = parseInt(section.querySelector('.length-value').value) || 0;
        const quantity = parseInt(section.querySelector('.length-quantity').value) || 0;

        if (length && quantity) {
            totalLength += length * quantity;
            sections.push(`${quantity}x${length}m`);
        }
    });

    console.log('Nowa całkowita długość:', totalLength);
    console.log('Sekcje:', sections);

    totalLengthInput.value = totalLength || '';
    textarea.value = sections.join(', ');
}

function initializeSpecificLengths(cableForm, lengthsData) {
    if (!lengthsData) return;

    const sectionsContainer = cableForm.querySelector('.length-sections-container');
    const packagingSelect = cableForm.querySelector('select[name*="packaging"]');
    const specificLengthsField = cableForm.querySelector('.specific-lengths-field');

    if (packagingSelect.value === 'dokładne odcinki') {
        specificLengthsField.style.display = 'block';

        // Wyczyść istniejące sekcje
        sectionsContainer.innerHTML = '';

        // Parsuj dane o odcinkach
        const sections = lengthsData.split(',').map(section => {
            const [quantity, length] = section.trim().split('x');
            return {
                quantity: parseInt(quantity),
                length: parseInt(length)
            };
        });

        // Dodaj sekcje
        sections.forEach(section => {
            const lengthSection = document.createElement('div');
            lengthSection.className = 'length-section d-flex gap-2 align-items-center mb-2';

            const lengthInput = document.createElement('input');
            lengthInput.type = 'number';
            lengthInput.className = 'form-control form-control-sm length-value';
            lengthInput.value = section.length;

            const quantityInput = document.createElement('input');
            quantityInput.type = 'number';
            quantityInput.className = 'form-control form-control-sm length-quantity';
            quantityInput.value = section.quantity;

            lengthSection.appendChild(lengthInput);
            lengthSection.appendChild(quantityInput);

            // Dodaj przycisk usuwania dla dodatkowych sekcji
            if (sectionsContainer.children.length > 0) {
                const removeButton = document.createElement('button');
                removeButton.type = 'button';
                removeButton.className = 'btn btn-danger btn-sm ms-2';
                removeButton.innerHTML = '×';
                removeButton.onclick = () => {
                    lengthSection.remove();
                    updateTotalLength(sectionsContainer);
                };
                lengthSection.appendChild(removeButton);
            }

            sectionsContainer.appendChild(lengthSection);

            // Dodaj listenery do aktualizacji całkowitej długości
            [lengthInput, quantityInput].forEach(input => {
                input.addEventListener('input', () => updateTotalLength(sectionsContainer));
            });
        });

        // Aktualizuj całkowitą długość
        updateTotalLength(sectionsContainer);
    }
}


// Inicjalizacja przycisku dodawania kabla
function initializeAddCableButton() {
    const addCableButton = document.querySelector('#add-cable');
    if (addCableButton) {
        addCableButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Dodawanie nowego kabla');

            const cablesContainer = document.querySelector('#cable-forms');
            const cableFormTemplate = document.querySelector('.cable-form').cloneNode(true);

            // Aktualizacja indeksów i przygotowanie formularza
            const newIndex = cablesContainer.children.length;
            updateFormIndices(cableFormTemplate, newIndex);

            // Czyszczenie wartości
            clearFormInputs(cableFormTemplate);

            // Resetowanie sekcji voltage i specific lengths
            const voltageButtons = cableFormTemplate.querySelector('.voltage-buttons');
            const specificLengthsField = cableFormTemplate.querySelector('.specific-lengths-field');
            if (voltageButtons) voltageButtons.style.display = 'none';
            if (specificLengthsField) specificLengthsField.style.display = 'none';

            // Dodanie przycisku usuwania
            addRemoveButton(cableFormTemplate);

            // Dodanie formularza do kontenera
            cablesContainer.appendChild(cableFormTemplate);

            // Reinicjalizacja handlerów
            handleVoltageFields();
            handlePackagingFields();
        });
    }
}

function updateFormIndices(form, newIndex) {
    // Aktualizacja tytułu
    form.querySelector('.card-title').textContent = `Kabel #${newIndex + 1}`;

    // Aktualizacja wszystkich pól cables-*
    form.querySelectorAll('[name^="cables-"]').forEach(element => {
        const fieldName = element.name.split('-').pop();
        element.name = `cables-${newIndex}-${fieldName}`;
        element.id = `cables-${newIndex}-${fieldName}`;
    });

    // Aktualizacja przycisków voltage
    form.querySelectorAll('input[type="radio"][name^="voltage-"]').forEach(radio => {
        radio.name = `voltage-${newIndex}`;
        const oldId = radio.id;
        const newId = oldId.replace(/\d+$/, newIndex);
        radio.id = newId;

        // Aktualizacja powiązanego label
        const label = form.querySelector(`label[for="${oldId}"]`);
        if (label) {
            label.setAttribute('for', newId);
        }
    });
}

function clearFormInputs(form) {
    form.querySelectorAll('input, select, textarea').forEach(input => {
        if (input.type === 'radio') {
            input.checked = false;
        } else if (input.type !== 'hidden' && !input.classList.contains('keep-value')) {
            // Dla selecta konfekcji ustawiamy domyślną wartość 'pełne bębny'
            if (input.name.includes('packaging')) {
                input.value = 'pełne bębny';
            } else {
                input.value = '';
            }
        }
    });
}

function initializeRowHandlers() {
    console.log('Initializing row handlers...');

    // Sprawdź, czy w ogóle są jakieś wiersze
    const allRows = document.querySelectorAll('tr');
    console.log('Total table rows found:', allRows.length);

    // Obsługa klikania w wiersze
    const rows = document.querySelectorAll('.clickable-row');
    console.log('Clickable rows found:', rows.length);

    if (rows.length > 0) {
        console.log('First clickable row:', rows[0]);
        console.log('First row data-row-id:', rows[0].dataset.rowId);
    }

    rows.forEach((row, index) => {
        row.addEventListener('click', function(e) {
            console.log('Row clicked!');
            console.log('Event:', e);
            const rowId = this.dataset.rowId;
            console.log('Clicked row ID:', rowId);
            const actionRow = document.getElementById('actions-' + rowId);
            console.log('Found action row:', actionRow);

            if (actionRow) {
                // Zamknij wszystkie otwarte wiersze
                document.querySelectorAll('.action-row').forEach(openRow => {
                    if (openRow !== actionRow) {
                        openRow.style.display = 'none';
                    }
                });

                // Przełącz aktualny wiersz
                const currentDisplay = actionRow.style.display;
                console.log('Current display:', currentDisplay);
                actionRow.style.display = currentDisplay === 'none' ? 'table-row' : 'none';
                console.log('New display:', actionRow.style.display);
            } else {
                console.error('Action row not found for ID:', rowId);
            }
        });
    });
}

function initializeAllHandlers() {
    // Inicjalizacja wszystkich handlerów
    console.log('Inicjalizacja handlerów...');
    handleVoltageFields();
    handlePackagingFields();
    initializeAddCableButton();
    initializeRowHandlers();  // Dodaj tę linię
}

function addRemoveButton(form) {
    const removeButton = document.createElement('button');
    removeButton.textContent = 'Usuń kabel';
    removeButton.className = 'btn btn-danger mt-2';
    removeButton.type = 'button'; // Ważne, żeby nie submitował formularza
    removeButton.onclick = function(e) {
        e.preventDefault();
        form.remove();

        // Aktualizacja numeracji pozostałych formularzy
        const cablesContainer = document.querySelector('#cable-forms');
        cablesContainer.querySelectorAll('.cable-form').forEach((form, index) => {
            updateFormIndices(form, index);
        });
    };
    form.querySelector('.card-body').appendChild(removeButton);
}