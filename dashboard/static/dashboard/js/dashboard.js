document.addEventListener('DOMContentLoaded', function () {
    let trendsChart;
    const ctx = document.getElementById('trendsChart').getContext('2d');

    async function fetchAndUpdateData() {
        try {
            // Simulated API call with mock data
            const mockData = {
                totalConversations: 15234,
                conversationTrends: [
                    { date: '2024-03-01', count: 1200 },
                    { date: '2024-03-02', count: 1400 },
                    { date: '2024-03-03', count: 1100 },
                    { date: '2024-03-04', count: 1600 },
                    { date: '2024-03-05', count: 1800 },
                    { date: '2024-03-06', count: 1500 },
                    { date: '2024-03-07', count: 1700 }
                ],
                serviceStatuses: [
                    { name: 'Ollama Service', status: 'operational' },
                    { name: 'Astra DB', status: 'operational' },
                    { name: 'API Gateway', status: 'down' }
                ]
            };

            // Update total conversations
            document.getElementById('totalConversations').textContent = 
                mockData.totalConversations.toLocaleString();

            // Update status cards
            const statusCardsContainer = document.getElementById('statusCards');
            statusCardsContainer.innerHTML = mockData.serviceStatuses
                .map(service => `
                    <div class="col-md-4 mb-3">
                        <div class="card status-card h-100">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <h5 class="card-title mb-0">${service.name}</h5>
                                    <div class="d-flex align-items-center">
                                        <span class="status-indicator ${service.status === 'operational' ? 'status-operational' : 'status-down'}"></span>
                                        <span class="text-${service.status === 'operational' ? 'success' : 'danger'}">
                                            ${service.status === 'operational' ? 'Operational' : 'Down'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');

            // Update chart
            const chartData = {
                labels: mockData.conversationTrends.map(item => item.date),
                datasets: [{
                    label: 'Conversations',
                    data: mockData.conversationTrends.map(item => item.count),
                    borderColor: '#1a73e8',
                    backgroundColor: 'rgba(26, 115, 232, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            };

            const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            };

            if (trendsChart) {
                trendsChart.data = chartData;
                trendsChart.update();
            } else {
                trendsChart = new Chart(ctx, {
                    type: 'line',
                    data: chartData,
                    options: chartOptions
                });
            }

        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }

    // Initial data fetch
    fetchAndUpdateData();

    // Update data every 30 seconds
    setInterval(fetchAndUpdateData, 30000);
});
