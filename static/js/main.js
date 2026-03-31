// Auto close flash messages after 3 seconds
setTimeout(function() {
    let alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        alert.style.transition = 'opacity 0.5s';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 500);
    });
}, 3000);

// Update cart count in navbar
function updateCartCount() {
    fetch('/cart/count')
        .then(response => response.json())
        .then(data => {
            let cartBadge = document.getElementById('cart-count');
            if (cartBadge) {
                cartBadge.innerText = data.count;
                if (data.count > 0) {
                    cartBadge.style.display = 'inline';
                } else {
                    cartBadge.style.display = 'none';
                }
            }
        })
        .catch(err => console.log('Cart count error:', err));
}

// Update cart count on page load
updateCartCount();

// Loading Spinner - Smart Version
function showSpinner() {
    document.getElementById('loading-spinner').style.display = 'flex';
}

function hideSpinner() {
    document.getElementById('loading-spinner').style.display = 'none';
}

// Hide spinner when page fully loads
window.addEventListener('load', hideSpinner);

// Show spinner only on main navigation links
document.addEventListener('click', function(e) {
    let target = e.target.closest('a');
    if (target && 
        target.href && 
        !target.href.startsWith('#') &&
        !target.href.includes('javascript') &&
        !target.href.includes('/cart/remove') &&
        !target.href.includes('/wishlist/remove') &&
        !target.href.includes('/admin/categories/delete') &&
        !target.href.includes('/admin/products/delete') &&
        !target.href.includes('/logout') &&
        target.target !== '_blank') {
        showSpinner();
    }
});

// Show spinner on form submit
document.addEventListener('submit', function() {
    showSpinner();
});

// Hide spinner if back button pressed
window.addEventListener('pageshow', function(e) {
    if (e.persisted) {
        hideSpinner();
    }
});

// Safety - hide spinner after 3 seconds max
setTimeout(hideSpinner, 3000);