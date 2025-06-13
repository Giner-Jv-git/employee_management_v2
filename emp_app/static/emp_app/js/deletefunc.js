function confirmDelete(pk, name) {
    if (confirm(`Are you sure you want to delete "${name}"?`)) {
        window.location.href = `/employees/delete/${pk}/`;
    }
}


document.addEventListener('DOMContentLoaded', function() {
    const deletedEmployeeName = sessionStorage.getItem('deletedEmployeeName');
    if (deletedEmployeeName) {
        
        sessionStorage.removeItem('deletedEmployeeName');
    }
});