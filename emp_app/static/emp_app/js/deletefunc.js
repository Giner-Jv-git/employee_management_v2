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


document.querySelector('form').addEventListener('submit', function(e) {
    if (!confirm('🏖️ Are you absolutely sure you want to erase this beach memory? This action cannot be undone!')) {
        e.preventDefault();
    }
});

// Add floating animation to cards
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.backdrop-blur-sm');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});