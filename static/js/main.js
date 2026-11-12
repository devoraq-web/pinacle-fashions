/**
 * PINACLE FASHIONS - LUXURY STOREFRONT CORE JAVASCRIPT
 * Modular event-delegated interactivity: Sticky Nav, Quick View, Zoom, Wishlist,
 * AJAX Bag, Review Carousel, Scroll Reveals, Subtle Card Tilt & Safe Toasts
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isFinePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

    // 1. Sticky Header Scroll Elevation
    const header = document.getElementById('pfHeader');
    const syncHeaderScroll = () => {
        if (!header) return;
        const scrolled = window.scrollY > 36;
        header.classList.toggle('scrolled', scrolled);
        header.classList.toggle('pf-navbar--scrolled', scrolled);
    };
    window.addEventListener('scroll', syncHeaderScroll, { passive: true });
    syncHeaderScroll();

    // 2. Focus Search Input when Header Search Bar Expands
    const searchCollapse = document.getElementById('searchCollapseBar');
    if (searchCollapse) {
        searchCollapse.addEventListener('shown.bs.collapse', () => {
            const input = document.getElementById('headerSearchInput');
            if (input) input.focus();
        });
    }

    // 3. IntersectionObserver Scroll Reveals (.pf-reveal)
    const revealEls = document.querySelectorAll('.pf-reveal');
    if (!prefersReducedMotion && 'IntersectionObserver' in window && revealEls.length > 0) {
        document.documentElement.classList.add('js-reveal-enabled');
        const observer = new IntersectionObserver(
            (entries, obs) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.08, rootMargin: '0px 0px -30px 0px' }
        );
        revealEls.forEach((el) => observer.observe(el));
    } else {
        revealEls.forEach((el) => el.classList.add('is-visible'));
    }

    // 4. Subtle Desktop-Only 3D Tilt on Product Cards (never active on touch devices)
    if (isFinePointer && !prefersReducedMotion) {
        document.querySelectorAll('.pf-product-card').forEach((card) => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width - 0.5;
                const y = (e.clientY - rect.top) / rect.height - 0.5;
                card.style.transform = `translateY(-6px) perspective(900px) rotateX(${(-y * 3).toFixed(2)}deg) rotateY(${(x * 3).toFixed(2)}deg)`;
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    // 5. Horizontal Customer Reviews Carousel Controls
    const reviewTrack = document.getElementById('pfReviewTrack');
    const reviewPrevBtn = document.getElementById('reviewPrevBtn');
    const reviewNextBtn = document.getElementById('reviewNextBtn');
    if (reviewTrack) {
        const scrollAmount = () => Math.max(reviewTrack.clientWidth * 0.72, 300);
        if (reviewPrevBtn) {
            reviewPrevBtn.addEventListener('click', () => {
                reviewTrack.scrollBy({ left: -scrollAmount(), behavior: prefersReducedMotion ? 'auto' : 'smooth' });
            });
        }
        if (reviewNextBtn) {
            reviewNextBtn.addEventListener('click', () => {
                reviewTrack.scrollBy({ left: scrollAmount(), behavior: prefersReducedMotion ? 'auto' : 'smooth' });
            });
        }
    }

    // 6. Product Detail Interactive Zoom & Cursor Tracking
    const zoomContainer = document.getElementById('pfZoomContainer');
    const detailMainImg = document.getElementById('pfDetailMainImg');
    if (zoomContainer && detailMainImg) {
        const updateZoomOrigin = (e) => {
            const rect = zoomContainer.getBoundingClientRect();
            const xPct = Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100));
            const yPct = Math.min(100, Math.max(0, ((e.clientY - rect.top) / rect.height) * 100));
            detailMainImg.style.transformOrigin = `${xPct.toFixed(1)}% ${yPct.toFixed(1)}%`;
        };
        zoomContainer.addEventListener('click', (e) => {
            zoomContainer.classList.toggle('is-zoomed');
            updateZoomOrigin(e);
        });
        zoomContainer.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                zoomContainer.classList.toggle('is-zoomed');
            }
        });
        zoomContainer.addEventListener('mousemove', (e) => {
            if (zoomContainer.classList.contains('is-zoomed')) {
                updateZoomOrigin(e);
            }
        });
        zoomContainer.addEventListener('mouseleave', () => {
            zoomContainer.classList.remove('is-zoomed');
            detailMainImg.style.transformOrigin = 'center center';
        });
    }

    // 7. Helper to Sync Buy Now WhatsApp Checkout Link Params
    function syncBuyNowUrl(rootSelector, btnSelector) {
        const btn = document.querySelector(btnSelector);
        const root = document.querySelector(rootSelector);
        if (!btn || !root) return;

        const baseUrl = btn.dataset.baseUrl;
        if (!baseUrl) return;

        const url = new URL(baseUrl, window.location.origin);
        const qtyInput = root.querySelector('input[name="quantity"]');
        const sizeInput = root.querySelector('input[name="size"]:checked');
        const colourInput = root.querySelector('input[name="colour"]:checked');

        if (qtyInput) url.searchParams.set('quantity', qtyInput.value || '1');
        if (sizeInput) url.searchParams.set('size', sizeInput.value);
        if (colourInput) url.searchParams.set('colour', colourInput.value);

        btn.href = url.pathname + url.search;
    }

    // 8. Global Event Delegation (handles static + dynamic Quick View modal DOM)
    document.addEventListener('click', (e) => {
        // A) Wishlist Toggle
        const wishlistBtn = e.target.closest('.btn-wishlist-toggle');
        if (wishlistBtn) {
            e.preventDefault();
            const url = wishlistBtn.dataset.url;
            const prodId = wishlistBtn.dataset.productId;
            if (!url) return;

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (!data.success) return;
                    const buttons = prodId
                        ? document.querySelectorAll(`.btn-wishlist-toggle[data-product-id="${prodId}"]`)
                        : [wishlistBtn];

                    buttons.forEach((btn) => {
                        const icon = btn.querySelector('i');
                        if (data.added) {
                            btn.classList.add('active');
                            if (icon) {
                                icon.classList.remove('far');
                                icon.classList.add('fas');
                            }
                        } else {
                            btn.classList.remove('active');
                            if (icon) {
                                icon.classList.remove('fas');
                                icon.classList.add('far');
                            }
                        }
                    });

                    const badge = document.getElementById('header-wishlist-count');
                    if (badge) {
                        badge.textContent = data.wishlist_count;
                        badge.classList.toggle('d-none', !data.wishlist_count);
                    }
                    showToast('Wishlist', data.message, 'info');
                })
                .catch(() => {
                    showToast('Notice', 'Could not update your wishlist right now.', 'danger');
                });
            return;
        }

        // B) Quick View Modal Trigger
        const quickViewBtn = e.target.closest('.btn-quick-view');
        if (quickViewBtn) {
            e.preventDefault();
            const url = quickViewBtn.dataset.url;
            const modalEl = document.getElementById('quickViewModal');
            const contentEl = document.getElementById('quickViewContent');
            if (!url || !modalEl || !contentEl) return;

            const qvModal = bootstrap.Modal.getOrCreateInstance(modalEl);
            contentEl.innerHTML =
                '<div class="text-center py-5"><div class="spinner-border text-gold" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            qvModal.show();

            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        contentEl.innerHTML = data.html;
                    } else {
                        contentEl.innerHTML = '<div class="alert alert-danger m-3">Unable to load creation details.</div>';
                    }
                })
                .catch(() => {
                    contentEl.innerHTML = '<div class="alert alert-danger m-3">Unable to load creation details.</div>';
                });
            return;
        }

        // C) Thumbnail Switching (Product Detail + Quick View)
        const detailThumb = e.target.closest('.pf-detail-thumb-btn');
        if (detailThumb && detailMainImg) {
            const nextSrc = detailThumb.dataset.imgSrc;
            if (nextSrc) {
                detailMainImg.src = nextSrc;
                document.querySelectorAll('.pf-detail-thumb-btn').forEach((b) => b.classList.remove('active'));
                detailThumb.classList.add('active');
            }
            return;
        }

        const qvThumb = e.target.closest('.qv-thumb-btn');
        if (qvThumb) {
            const qvMain = document.getElementById('qvMainImg');
            const nextSrc = qvThumb.dataset.imgSrc;
            if (qvMain && nextSrc) {
                qvMain.src = nextSrc;
                document.querySelectorAll('.qv-thumb-btn').forEach((b) => b.classList.remove('active'));
                qvThumb.classList.add('active');
            }
            return;
        }

        // D) Quantity Stepper Buttons (Product Detail + Quick View)
        const detailMinus = e.target.closest('#detailQtyMinus');
        const detailPlus = e.target.closest('#detailQtyPlus');
        if (detailMinus || detailPlus) {
            const input = document.getElementById('detailQtyInput');
            if (input) {
                const max = parseInt(input.max || '99', 10);
                let val = parseInt(input.value || '1', 10);
                val = detailPlus ? Math.min(max, val + 1) : Math.max(1, val - 1);
                input.value = val;
                syncBuyNowUrl('#detailAddToCartForm', '#detailBuyNowBtn');
            }
            return;
        }

        const qvMinus = e.target.closest('.qv-qty-minus');
        const qvPlus = e.target.closest('.qv-qty-plus');
        if (qvMinus || qvPlus) {
            const input = document.getElementById('qvQtyInput');
            if (input) {
                const max = parseInt(input.max || '99', 10);
                let val = parseInt(input.value || '1', 10);
                val = qvPlus ? Math.min(max, val + 1) : Math.max(1, val - 1);
                input.value = val;
                syncBuyNowUrl('#quickViewAddToCartForm', '#quickViewBuyNowBtn');
            }
            return;
        }
    });

    // Update Buy Now URL when Size or Colour pills change
    document.addEventListener('change', (e) => {
        if (e.target.closest('.detail-option-input')) {
            syncBuyNowUrl('#detailAddToCartForm', '#detailBuyNowBtn');
        }
        if (e.target.closest('.qv-option-input')) {
            syncBuyNowUrl('#quickViewAddToCartForm', '#quickViewBuyNowBtn');
        }
    });

    // 9. Global Delegated AJAX Form Submissions (Add to Bag + Newsletter)
    document.addEventListener('submit', (e) => {
        const cartForm = e.target.closest('.ajax-add-to-cart-form');
        if (cartForm) {
            e.preventDefault();
            const formData = new FormData(cartForm);
            const submitBtn = cartForm.querySelector('button[type="submit"]');
            const origHtml = submitBtn ? submitBtn.innerHTML : '';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span> Adding...';
            }

            fetch(cartForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showToast('Bag Updated', data.message, 'success');
                        const cartCountEl = document.getElementById('header-cart-count');
                        if (cartCountEl) {
                            cartCountEl.textContent = data.cart_count ?? 0;
                            cartCountEl.classList.remove('d-none');
                        }
                    } else {
                        showToast('Notice', data.message || 'Could not add item to bag.', 'danger');
                    }
                })
                .catch(() => {
                    showToast('Notice', 'Could not add item to bag. Please try again.', 'danger');
                })
                .finally(() => {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = origHtml;
                    }
                });
            return;
        }

        const nlForm = e.target.closest('.ajax-newsletter-form');
        if (nlForm) {
            e.preventDefault();
            const formData = new FormData(nlForm);
            fetch(nlForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showToast('VIP List', data.message, 'success');
                        nlForm.reset();
                    } else {
                        showToast('Notice', data.message || 'Please enter a valid email address.', 'danger');
                    }
                })
                .catch(() => {
                    showToast('Notice', 'Unable to subscribe right now. Please try again.', 'danger');
                });
        }
    });
});

/**
 * Retrieve CSRF token from cookie, meta tag, or hidden input
 */
function getCsrfToken() {
    if (document.cookie) {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return decodeURIComponent(cookie.substring(10));
            }
        }
    }
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken && metaToken.content) return metaToken.content;

    const inputToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return inputToken ? inputToken.value : '';
}

/**
 * XSS-Safe Toast Notification Popup Helper (uses DOM textContent instead of raw HTML)
 */
function showToast(title, message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    const bgClass =
        type === 'success'
            ? 'bg-dark text-white'
            : type === 'danger'
            ? 'bg-danger text-white'
            : 'bg-light text-dark';

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center ${bgClass} border-0 shadow-lg mb-2`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    const row = document.createElement('div');
    row.className = 'd-flex';

    const body = document.createElement('div');
    body.className = 'toast-body';
    const strong = document.createElement('strong');
    strong.textContent = `${title}: `;
    body.appendChild(strong);
    body.appendChild(document.createTextNode(String(message || '')));

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = type === 'info' ? 'btn-close me-2 m-auto' : 'btn-close btn-close-white me-2 m-auto';
    closeBtn.setAttribute('data-bs-dismiss', 'toast');
    closeBtn.setAttribute('aria-label', 'Close');

    row.appendChild(body);
    row.appendChild(closeBtn);
    toastEl.appendChild(row);
    toastContainer.appendChild(toastEl);

    const toast = new bootstrap.Toast(toastEl, { delay: 3800 });
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}
