document.addEventListener('DOMContentLoaded', function () {
    console.log('Inicjalizacja obsługi tablicy...');
    initializeTableHandlers();
    setupDarkMode();
});

function initializeTableHandlers() {
    const rows = document.querySelectorAll('.clickable-row');
    console.log('Znaleziono klikalnych wierszy:', rows.length);

    // Obsługa wierszy
    rows.forEach(row => {
        row.addEventListener('click', function (event) {
            // Zatrzymaj propagację dla przycisków i formularzy
            if (event.target.closest('button') ||
                event.target.closest('a') ||
                event.target.closest('form') ||
                event.target.closest('.btn-group') ||
                event.target.closest('input')) { // Dodano input do ignorowanych
                return;
            }

            const rowId = this.dataset.rowId;
            console.log('Kliknięto wiersz:', rowId);

            // Znajdujemy odpowiedni wiersz z akcjami
            const actionRow = document.getElementById(`actions-${rowId}`);

            if (!actionRow) {
                console.error('Nie znaleziono wiersza akcji:', rowId);
                return;
            }

            // Zamykamy wszystkie inne otwarte wiersze
            document.querySelectorAll('.action-row').forEach(row => {
                if (row !== actionRow) {
                    row.style.display = 'none';
                }
            });

            // Przełączamy widoczność klikniętego wiersza
            actionRow.style.display = actionRow.style.display === 'table-row' ? 'none' : 'table-row';
        });
    });

    // Obsługa filtrów
    document.querySelectorAll('#filterForm select').forEach(select => {
        select.addEventListener('change', function () {
            this.closest('form').submit();
        });
    });

    setupSearch();
}

function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    searchInput.addEventListener('keyup', function () {
        const searchText = this.value.toLowerCase().trim();
        const rows = document.querySelectorAll('.clickable-row');

        rows.forEach(row => {
            const rowText = row.textContent.toLowerCase();
            const shouldShow = rowText.includes(searchText);

            // Pokaż/ukryj główny wiersz
            row.style.display = shouldShow ? '' : 'none';

            // Jeśli ukrywamy główny wiersz, upewnij się że wiersz akcji też jest ukryty
            if (!shouldShow) {
                const rowId = row.dataset.rowId;
                const actionRow = document.getElementById(`actions-${rowId}`);
                if (actionRow) {
                    actionRow.style.display = 'none';
                }
            }
        });
    });
}

function setupDarkMode() {
    const toggleSwitch = document.querySelector('#theme-toggle');
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme) {
        document.documentElement.setAttribute('data-theme', currentTheme);
        if (currentTheme === 'dark' && toggleSwitch) {
            toggleSwitch.checked = true;
        }
    }

    if (toggleSwitch) {
        // Usuń stare event listenery (poprzez klonowanie, trick) lub po prostu dodaj nowy
        // W tym przypadku zakładamy, że to jedyny listener w tym pliku dla tego elementu
        toggleSwitch.addEventListener('change', function (e) {
            if (e.target.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
        });
    }
}

// Funkcja do oznaczania komentarzy jako przeczytane/nieprzeczytane
function toggleCommentsRead(queryId, isRead) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

    fetch(`/toggle-comments-read/${queryId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ is_read: isRead })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                window.location.reload();
            } else {
                console.error('Error updating comments status:', data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });

    // Zatrzymaj propagację zdarzenia
    event.stopPropagation();
}