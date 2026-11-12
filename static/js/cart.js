/**
 * PINACLE FASHIONS - SHOPPING CART JAVASCRIPT
 * Handles AJAX quantity updates, removals, subtotal calculations, and checkout triggers
 */

document.addEventListener('DOMContentLoaded', () => {
    // Quantity increment & decrement in cart table
    document.querySelectorAll('.cart-qty-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemKey = this.dataset.itemKey;
            const action = this.dataset.action; // 'plus' or 'minus'
            const input = document.querySelector(`.cart-qty-input[data-item-key="${itemKey}"]`);
            if (!input) return;

            let currentVal = parseInt(input.value) || 1;
            let newVal = action === 'plus' ? currentVal + 1 : currentVal - 1;

            if (newVal < 1) newVal = 1;
            input.value = newVal;

            updateCartItem(itemKey, newVal);
        });
    });

    // Direct input change
    document.querySelectorAll('.cart-qty-input').forEach(input => {
        input.addEventListener('change', function() {
            const itemKey = this.dataset.itemKey;
            let val = parseInt(this.value) || 1;
            if (val < 1) val = 1;
            this.value = val;
            updateCartItem(itemKey, val);
        });
    });

    // Remove item from cart via AJAX
    document.querySelectorAll('.cart-remove-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const itemKey = this.dataset.itemKey;
            if (!itemKey) return;

            if (confirm("Remove this item from your shopping bag?")) {
                const row = document.getElementById(`cart-row-${itemKey}`);
                
                fetch(`/cart/remove/${encodeURIComponent(itemKey)}/`, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCsrfToken()
                    }
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        if (row) {
                            row.style.transition = 'opacity 0.3s ease';
                            row.style.opacity = '0';
                            setTimeout(() => {
                                row.remove();
                                // Check if cart is now empty
                                const remainingRows = document.querySelectorAll('.cart-item-row');
                                if (remainingRows.length === 0) {
                                    location.reload(); // Reload to render empty cart state
                                }
                            }, 300);
                        }
                        updateCartTotalsUI(data.cart_subtotal, data.cart_count);
                        showToast('Cart Updated', 'Item removed from bag.', 'info');
                    }
                })
                .catch(err => console.error(err));
            }
        });
    });
});

function updateCartItem(itemKey, quantity) {
    const formData = new FormData();
    formData.append('item_key', itemKey);
    formData.append('quantity', quantity);

    fetch('/cart/update/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            updateCartTotalsUI(data.cart_subtotal, data.cart_count);
            // Recalculate item total in UI
            const unitPriceEl = document.querySelector(`.cart-unit-price[data-item-key="${itemKey}"]`);
            const itemTotalEl = document.querySelector(`.cart-item-total[data-item-key="${itemKey}"]`);
            if (unitPriceEl && itemTotalEl) {
                const unitPrice = parseFloat(unitPriceEl.dataset.price);
                const itemTotal = (unitPrice * quantity).toFixed(2);
                itemTotalEl.textContent = `₹${itemTotal}`;
            }
        }
    })
    .catch(err => console.error(err));
}

function updateCartTotalsUI(subtotal, count) {
    const subtotalEl = document.getElementById('cart-subtotal-val');
    const grandTotalEl = document.getElementById('cart-grand-total-val');
    const headerCountEl = document.getElementById('header-cart-count');

    if (subtotalEl) subtotalEl.textContent = `₹${subtotal}`;
    if (grandTotalEl) grandTotalEl.textContent = `₹${subtotal}`;
    if (headerCountEl) {
        headerCountEl.textContent = count ?? 0;
        headerCountEl.classList.remove('d-none');
    }
}

