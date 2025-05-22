document.addEventListener('DOMContentLoaded', function() {
    // Auto-submit form when period selection changes
    const periodRadios = document.querySelectorAll('input[name="period"]');
    periodRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            document.getElementById('stock-form').submit();
        });
    });

    // Add animation to chart on load
    const chartImage = document.querySelector('.stock-chart');
    if (chartImage) {
        chartImage.style.opacity = '0';
        chartImage.style.transition = 'opacity 0.5s ease-in';
        
        chartImage.addEventListener('load', function() {
            setTimeout(() => {
                chartImage.style.opacity = '1';
            }, 100);
        });
        
        // If the image is already loaded, make it visible
        if (chartImage.complete) {
            chartImage.style.opacity = '1';
        }
    }
    
    // Enable Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Add validation styling to form
    const stockForm = document.getElementById('stock-form');
    if (stockForm) {
        stockForm.addEventListener('submit', function(event) {
            if (!stockForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            stockForm.classList.add('was-validated');
        });
    }
});
