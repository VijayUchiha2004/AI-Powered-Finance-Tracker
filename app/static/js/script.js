// Chart.js defaults
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#64748b';
Chart.defaults.scale.grid.color = '#e2e8f0';

// Global chart instances
let spendingTrendsChart;
let categoryChart;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initializeCharts();
    
    // Load initial data
    loadUserInfo();
    loadQuickStats();
    loadTransactions();
    loadSpendingAnalysis();

    // Set up form handlers
    document.getElementById('transactionForm').addEventListener('submit', handleTransactionSubmit);

    // Set up period buttons
    document.querySelectorAll('.period-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            document.querySelectorAll('.period-btn').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            loadSpendingAnalysis(e.target.textContent.toLowerCase());
        });
    });

    checkAuth();
    
    // Add logout button to navbar if it doesn't exist
    const navbar = document.querySelector('.navbar');
    if (!document.querySelector('.logout-btn')) {
        const logoutBtn = document.createElement('button');
        logoutBtn.className = 'logout-btn';
        logoutBtn.onclick = logout;
        logoutBtn.innerHTML = `
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
            </svg>
            Logout
        `;
        navbar.appendChild(logoutBtn);
    }
});

function initializeCharts() {
    // Spending Trends Chart
    const spendingCtx = document.getElementById('spendingTrendsChart').getContext('2d');
    spendingTrendsChart = new Chart(spendingCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Daily Spending',
                data: [],
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: '#1e293b',
                    titleColor: '#f1f5f9',
                    bodyColor: '#f1f5f9',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `$${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: value => `$${value}`
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });

    // Category Distribution Chart
    const categoryCtx = document.getElementById('categoryChart').getContext('2d');
    categoryChart = new Chart(categoryCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#2563eb',
                    '#3b82f6',
                    '#60a5fa',
                    '#93c5fd',
                    '#bfdbfe'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                }
            },
            cutout: '75%'
        }
    });
}

async function loadUserInfo() {
    try {
        const response = await fetch('/api/user');
        const user = await response.json();
        document.querySelector('.user-name').textContent = user.name;
        document.querySelector('.user-email').textContent = user.email;
    } catch (error) {
        console.error('Error loading user info:', error);
        showErrorToast('Failed to load user information');
    }
}

async function loadQuickStats() {
    try {
        const response = await fetch('/api/quick-stats');
        const stats = await response.json();
        
        updateStatCard('totalSpending', stats.total_spending, 'Total Spending');
        updateStatCard('monthlyAverage', stats.monthly_average, 'Monthly Average');
        updateStatCard('largestExpense', stats.largest_expense, 'Largest Expense');
        updateStatCard('transactionCount', stats.transaction_count, 'Total Transactions', false);
    } catch (error) {
        console.error('Error loading quick stats:', error);
        showErrorToast('Failed to load statistics');
    }
}

function updateStatCard(id, value, label, isCurrency = true) {
    const card = document.getElementById(id);
    const valueElement = card.querySelector('.value');
    
    if (value === 0) {
        valueElement.innerHTML = `<span class="empty-state">No data yet</span>`;
        return;
    }
    
    if (isCurrency) {
        valueElement.textContent = formatCurrency(value);
    } else {
        valueElement.textContent = value;
    }
}

async function loadTransactions() {
    try {
        const response = await fetch('/api/transactions');
        const transactions = await response.json();
        
        const transactionsList = document.getElementById('recentTransactions');
        
        if (!transactions.length) {
            transactionsList.innerHTML = `
                <div class="empty-state">
                    <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <p>No transactions yet</p>
                    <button class="add-transaction-btn" onclick="showAddTransactionModal()">
                        Add Your First Transaction
                    </button>
                </div>
            `;
            return;
        }
        
        transactionsList.innerHTML = transactions.map(transaction => `
            <div class="transaction-item ${transaction.amount < 0 ? 'expense' : 'income'}">
                <div class="transaction-info">
                    <span class="description">${transaction.description}</span>
                    <span class="category">${transaction.category}</span>
                </div>
                <span class="amount">
                    ${formatCurrency(Math.abs(transaction.amount))}
                </span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading transactions:', error);
        showErrorToast('Failed to load transactions');
    }
}

async function loadSpendingAnalysis(period = 'month') {
    try {
        const response = await fetch(`/api/analysis?period=${period}`);
        const data = await response.json();
        
        // Update spending trends chart
        if (spendingTrendsChart) {
            spendingTrendsChart.data.labels = data.spending_trends.dates.map(date => 
                new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            );
            spendingTrendsChart.data.datasets[0].data = data.spending_trends.amounts;
            spendingTrendsChart.update();
        }

        // Update category chart
        if (categoryChart) {
            const categories = Object.keys(data.category_totals);
            const amounts = Object.values(data.category_totals);
            
            categoryChart.data.labels = categories;
            categoryChart.data.datasets[0].data = amounts;
            categoryChart.update();
        }
    } catch (error) {
        console.error('Error loading spending analysis:', error);
        showErrorToast('Failed to load analysis');
    }
}

async function handleTransactionSubmit(e) {
    e.preventDefault();
    
    const formData = {
        amount: parseFloat(document.getElementById('amount').value),
        description: document.getElementById('description').value,
        category: document.getElementById('category').value
    };

    try {
        const response = await fetch('/api/transactions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            showSuccessToast('Transaction added successfully');
            closeAddTransactionModal();
            // Reload data
            loadQuickStats();
            loadTransactions();
            loadSpendingAnalysis();
        } else {
            throw new Error('Failed to add transaction');
        }
    } catch (error) {
        console.error('Error adding transaction:', error);
        showErrorToast('Failed to add transaction');
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function showAddTransactionModal() {
    document.getElementById('addTransactionModal').style.display = 'flex';
    document.getElementById('amount').focus();
}

function closeAddTransactionModal() {
    document.getElementById('addTransactionModal').style.display = 'none';
    document.getElementById('transactionForm').reset();
}

// Toast notification enhancements
function showToast(message, type = 'success', duration = 3000) {
    const toastContainer = document.getElementById('toastContainer');
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Add progress bar for auto-dismiss
    const progressBar = document.createElement('div');
    progressBar.className = 'toast-progress';
    
    // Different icons for different types
    const icons = {
        success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`,
        error: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`,
        warning: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`,
        info: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`
    };
    
    // Set toast content
    toast.innerHTML = `
        ${icons[type] || icons.info}
        <div class="toast-content">
            <span class="toast-message">${message}</span>
        </div>
        <button class="toast-close" onclick="dismissToast(this.parentElement)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M6 18L18 6M6 6l12 12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </button>
        ${progressBar.outerHTML}
    `;
    
    // Add toast to container
    toastContainer.appendChild(toast);
    
    // Trigger animations
    requestAnimationFrame(() => {
        toast.classList.add('show');
        progressBar.style.transition = `width ${duration}ms linear`;
        progressBar.style.width = '0%';
    });
    
    // Set up auto-dismiss
    const timeoutId = setTimeout(() => dismissToast(toast), duration);
    
    // Store timeout ID for potential manual dismiss
    toast.dataset.timeoutId = timeoutId;
    
    // Pause progress bar on hover
    toast.addEventListener('mouseenter', () => {
        clearTimeout(timeoutId);
        progressBar.style.transition = 'none';
    });
    
    // Resume progress bar on mouse leave
    toast.addEventListener('mouseleave', () => {
        const remainingTime = parseInt(progressBar.style.width) * duration / 100;
        toast.dataset.timeoutId = setTimeout(() => dismissToast(toast), remainingTime);
        progressBar.style.transition = `width ${remainingTime}ms linear`;
        progressBar.style.width = '0%';
    });
}

function dismissToast(toast) {
    clearTimeout(toast.dataset.timeoutId);
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
}

// Helper functions for different toast types
function showSuccessToast(message) {
    showToast(message, 'success');
}

function showErrorToast(message) {
    showToast(message, 'error');
}

function showWarningToast(message) {
    showToast(message, 'warning');
}

function showInfoToast(message) {
    showToast(message, 'info');
}

function logout() {
    window.location.href = '/auth/logout';
}

function switchPage(pageName) {
    // Update navigation
    document.querySelectorAll('.nav-links li').forEach(li => {
        li.classList.remove('active');
    });
    document.querySelector(`[data-page="${pageName}"]`).classList.add('active');

    // Update page visibility
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(`${pageName}-page`).classList.add('active');

    // Load page-specific data
    switch(pageName) {
        case 'dashboard':
            loadQuickStats();
            loadTransactions();
            loadSpendingAnalysis();
            break;
        case 'transactions':
            loadAllTransactions();
            break;
        case 'analytics':
            loadSpendingAnalysis();
            // Force charts to resize
            setTimeout(() => {
                if (spendingTrendsChart) spendingTrendsChart.resize();
                if (categoryChart) categoryChart.resize();
            }, 100);
            break;
    }
}

async function loadAllTransactions() {
    try {
        const response = await fetch('/api/transactions');
        const transactions = await response.json();
        
        const transactionsList = document.getElementById('allTransactions');
        
        if (!transactions.length) {
            transactionsList.innerHTML = `
                <div class="empty-state">
                    <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <p>No transactions yet</p>
                    <button class="add-transaction-btn" onclick="showAddTransactionModal()">
                        Add Your First Transaction
                    </button>
                </div>
            `;
            return;
        }
        
        transactionsList.innerHTML = transactions.map(transaction => `
            <div class="transaction-item ${transaction.amount < 0 ? 'expense' : 'income'}">
                <div class="transaction-info">
                    <span class="description">${transaction.description}</span>
                    <span class="category">${transaction.category}</span>
                    <span class="date">${new Date(transaction.date).toLocaleDateString()}</span>
                </div>
                <span class="amount">
                    ${formatCurrency(Math.abs(transaction.amount))}
                </span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading transactions:', error);
        showErrorToast('Failed to load transactions');
    }
}

// Check authentication status
async function checkAuth() {
    try {
        const response = await fetch('/api/check-auth');
        if (!response.ok) {
            window.location.href = '/login';
        }
    } catch (error) {
        window.location.href = '/login';
    }
}