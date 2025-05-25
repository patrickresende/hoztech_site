// Store JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Product gallery image switching
    const galleryThumbs = document.querySelectorAll('.product-gallery-thumb');
    const galleryMain = document.querySelector('.product-gallery-main');
    
    if (galleryThumbs.length && galleryMain) {
        galleryThumbs.forEach(thumb => {
            thumb.addEventListener('click', function() {
                const newSrc = this.getAttribute('data-full-image');
                galleryMain.src = newSrc;
                
                // Update active state
                galleryThumbs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }

    // Quantity input handling
    const quantityInputs = document.querySelectorAll('.quantity-input');
    quantityInputs.forEach(input => {
        const minusBtn = input.previousElementSibling;
        const plusBtn = input.nextElementSibling;
        
        if (minusBtn && plusBtn) {
            minusBtn.addEventListener('click', () => {
                const currentValue = parseInt(input.value);
                if (currentValue > 1) {
                    input.value = currentValue - 1;
                    updateCartItem(input);
                }
            });
            
            plusBtn.addEventListener('click', () => {
                const currentValue = parseInt(input.value);
                input.value = currentValue + 1;
                updateCartItem(input);
            });
            
            input.addEventListener('change', () => {
                if (parseInt(input.value) < 1) {
                    input.value = 1;
                }
                updateCartItem(input);
            });
        }
    });

    // Cart item update function
    function updateCartItem(input) {
        const form = input.closest('form');
        if (form) {
            const formData = new FormData(form);
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update cart total
                    const cartTotal = document.querySelector('.cart-total');
                    if (cartTotal) {
                        cartTotal.textContent = data.cart_total;
                    }
                    
                    // Update cart badge
                    const cartBadge = document.querySelector('.cart-badge');
                    if (cartBadge) {
                        cartBadge.textContent = data.cart_count;
                    }
                    
                    // Show success message
                    showNotification('Carrinho atualizado com sucesso!', 'success');
                } else {
                    showNotification('Erro ao atualizar o carrinho.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Erro ao atualizar o carrinho.', 'error');
            });
        }
    }

    // Notification system
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} notification`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Add show class after a small delay for animation
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    // Search form handling
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        const searchInput = searchForm.querySelector('input[type="search"]');
        const searchResults = document.querySelector('.search-results');
        
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            
            if (this.value.length >= 2) {
                searchTimeout = setTimeout(() => {
                    fetch(`/busca/?q=${encodeURIComponent(this.value)}`, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (searchResults) {
                            searchResults.innerHTML = data.html;
                            searchResults.classList.add('show');
                        }
                    })
                    .catch(error => console.error('Error:', error));
                }, 300);
            } else if (searchResults) {
                searchResults.classList.remove('show');
            }
        });
        
        // Close search results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchForm.contains(e.target) && searchResults) {
                searchResults.classList.remove('show');
            }
        });
    }

    // Add to cart animation
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const form = this.closest('form');
            if (form) {
                const formData = new FormData(form);
                
                fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update cart badge
                        const cartBadge = document.querySelector('.cart-badge');
                        if (cartBadge) {
                            cartBadge.textContent = data.cart_count;
                        }
                        
                        // Show success message
                        showNotification('Produto adicionado ao carrinho!', 'success');
                        
                        // Add animation class
                        this.classList.add('added');
                        setTimeout(() => {
                            this.classList.remove('added');
                        }, 1000);
                    } else {
                        showNotification('Erro ao adicionar produto ao carrinho.', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('Erro ao adicionar produto ao carrinho.', 'error');
                });
            }
        });
    });

    // Newsletter form handling
    const newsletterForm = document.querySelector('.newsletter-form');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Inscrição realizada com sucesso!', 'success');
                    this.reset();
                } else {
                    showNotification(data.message || 'Erro ao realizar inscrição.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Erro ao realizar inscrição.', 'error');
            });
        });
    }
}); 