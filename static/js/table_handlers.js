document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicjalizacja obsługi tablicy...');
    initializeTableHandlers(); // zmieniona nazwa
});

function initializeTableHandlers() {
    const rows = document.querySelectorAll('.clickable-row');
    console.log('Znaleziono klikalnych wierszy:', rows.length);

    // Obsługa wierszy
    rows.forEach(row => {
        row.addEventListener('click', function(event) {
            // Zatrzymaj propagację dla przycisków i formularzy
            if (event.target.closest('button') ||
                event.target.closest('a') ||
                event.target.closest('form') ||
                event.target.closest('.btn-group')) {
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
        select.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });
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