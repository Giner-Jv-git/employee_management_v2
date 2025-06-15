
function calculateDuration() {
    const startDate = document.getElementById('id_start_date').value;
    const endDate = document.getElementById('id_end_date').value;
    const durationDisplay = document.getElementById('duration-display');
    
    if (startDate && endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        const diffTime = Math.abs(end - start);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
        
        if (end >= start) {
            durationDisplay.innerHTML = `${diffDays} day${diffDays !== 1 ? 's' : ''}`;
            durationDisplay.className = 'text-2xl font-bold text-green-600 text-center';
        } else {
            durationDisplay.innerHTML = 'Invalid date range';
            durationDisplay.className = 'text-2xl font-bold text-red-600 text-center';
        }
    } else {
        durationDisplay.innerHTML = 'Select dates to see duration';
        durationDisplay.className = 'text-2xl font-bold text-blue-600 text-center';
    }
}

document.getElementById('id_start_date').addEventListener('change', calculateDuration);
document.getElementById('id_end_date').addEventListener('change', calculateDuration);