// Bar Chart
const statusCanvas = document.getElementById('statusBarChart');
const activeEmployees = parseInt(statusCanvas.dataset.active);
const inactiveEmployees = parseInt(statusCanvas.dataset.inactive);

const statusBarCtx = statusCanvas.getContext('2d');
new Chart(statusBarCtx, {
    type: 'bar',
    data: {
        labels: ['Active', 'Inactive'],
        datasets: [{
            label: 'Employees',
            data: [activeEmployees, inactiveEmployees],
            backgroundColor: ['#34d399', '#f87171'],
        }]
    },
    options: {
        responsive: false,
        plugins: {
            legend: { display: false }
        }
    }
});

// Pie Chart
const positionCanvas = document.getElementById('positionPieChart');
const positionLabels = positionCanvas.dataset.labels.split(',');
const positionData = positionCanvas.dataset.counts.split(',').map(Number);

const positionColors = [
    '#60a5fa', '#fbbf24', '#34d399', '#f87171',
    '#a78bfa', '#f472b6', '#facc15', '#38bdf8'
].slice(0, positionLabels.length);

const positionPieCtx = positionCanvas.getContext('2d');
new Chart(positionPieCtx, {
    type: 'pie',
    data: {
        labels: positionLabels,
        datasets: [{
            data: positionData,
            backgroundColor: positionColors,
        }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
    }
}
});
