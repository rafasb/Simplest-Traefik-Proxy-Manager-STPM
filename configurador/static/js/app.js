// Función para eliminar un servicio
function deleteService(serviceName) {
    if (confirm(`¿Estás seguro de que deseas eliminar el servicio "${serviceName}"?`)) {
        console.log('Deleting service:', serviceName);
        fetch(`/service/${encodeURIComponent(serviceName)}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                location.reload();
            } else {
                alert(`Error al eliminar el servicio: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al eliminar el servicio');
        });
    }
}

// Eventos para botones de backup y restore
document.addEventListener('DOMContentLoaded', function() {
    const backupBtn = document.getElementById('backupBtn');
    if (backupBtn) {
        backupBtn.addEventListener('click', function() {
            fetch('/backup', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error al crear el backup');
            });
        });
    }

    const restoreBtn = document.getElementById('restoreBtn');
    if (restoreBtn) {
        restoreBtn.addEventListener('click', function() {
            if (confirm('¿Estás seguro de que deseas restaurar la configuración desde el último backup? Esta acción no se puede deshacer.')) {
                fetch('/restore', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    location.reload();
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error al restaurar el backup');
                });
            }
        });
    }
});
