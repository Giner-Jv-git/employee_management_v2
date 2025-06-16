document.addEventListener('DOMContentLoaded', function() {
    const startDateInput = document.getElementById('id_start_date');
    const endDateInput = document.getElementById('id_end_date');
    const durationDisplay = document.getElementById('duration-display');
    
    function calculateDuration() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        
        if (startDate && endDate) {
            const start = new Date(startDate);
            const end = new Date(endDate);
            const diffTime = Math.abs(end - start);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
            
            if (end >= start) {
                durationDisplay.textContent = `${diffDays} day${diffDays !== 1 ? 's' : ''}`;
                durationDisplay.className = 'text-2xl font-bold text-blue-600 text-center';
            } else {
                durationDisplay.textContent = 'Invalid date range';
                durationDisplay.className = 'text-2xl font-bold text-red-600 text-center';
            }
        } else {
            durationDisplay.textContent = 'Select dates to see duration';
            durationDisplay.className = 'text-2xl font-bold text-blue-600 text-center';
        }
    }
    
    if (startDateInput && endDateInput) {
        startDateInput.addEventListener('change', calculateDuration);
        endDateInput.addEventListener('change', calculateDuration);
    }
});
</script>