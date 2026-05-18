document.addEventListener('DOMContentLoaded', () => {
    // Hide loader after page load
    const loader = document.getElementById('loader');
    if (loader) {
        setTimeout(() => {
            loader.style.opacity = '0';
            setTimeout(() => {
                loader.style.display = 'none';
            }, 500);
        }, 500);
    }

    // Initialize animate on scroll elements
    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.scroll-animate').forEach(el => {
        el.style.opacity = '0'; // Initial state before animation
        observer.observe(el);
    });

    // Add to Cart functionality
    document.querySelectorAll('.add-to-cart-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const foodId = this.dataset.id;
            
            // Show a little animation on the button
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            fetch(`/add_to_cart/${foodId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update cart badge
                    const badge = document.getElementById('cart-badge');
                    if (badge) {
                        badge.textContent = data.cart_count;
                        badge.classList.remove('hidden');
                        // Bounce animation
                        badge.classList.add('animate-bounce');
                        setTimeout(() => badge.classList.remove('animate-bounce'), 1000);
                    }
                    
                    this.innerHTML = '<i class="fas fa-check text-green-500"></i> Added';
                    setTimeout(() => {
                        this.innerHTML = originalText;
                    }, 2000);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.innerHTML = originalText;
            });
        });
    });

    // Cart Quantity Update
    document.querySelectorAll('.update-cart-btn').forEach(button => {
        button.addEventListener('click', function() {
            const foodId = this.dataset.id;
            const action = this.dataset.action;
            
            fetch(`/update_cart/${foodId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action: action })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reload page to reflect changes simply
                    window.location.reload();
                }
            });
        });
    });

    // Table Selection Logic for Booking
    const tableNodes = document.querySelectorAll('.table-node.table-available');
    const tableInput = document.getElementById('selected_table_id');
    const tableDisplay = document.getElementById('selected-table-display');

    tableNodes.forEach(node => {
        node.addEventListener('click', function() {
            // Remove selected class from all
            tableNodes.forEach(n => n.classList.remove('table-selected'));
            // Add selected class to clicked
            this.classList.add('table-selected');
            
            const tableId = this.dataset.id;
            const tableNum = this.dataset.number;
            const tableCap = this.dataset.capacity;
            
            tableInput.value = tableId;
            tableDisplay.innerHTML = `<span class="text-gradient-gold text-xl font-bold">Table ${tableNum}</span> <span class="text-sm text-gray-400">(${tableCap} Seats)</span>`;
            tableDisplay.classList.add('animate-fade-in');
        });
    });
    
    // Menu Filtering Logic
    const filterBtns = document.querySelectorAll('.filter-btn');
    const dietBtns = document.querySelectorAll('.diet-btn');
    const menuItems = document.querySelectorAll('.menu-item');
    const menuSearch = document.getElementById('menu-search');

    let currentCategory = '';
    let currentDiet = 'all';
    let currentSearch = '';

    // Store original text for highlighting
    menuItems.forEach(item => {
        const titleEl = item.querySelector('h3');
        const descEl = item.querySelector('p.line-clamp-2');
        if (titleEl) titleEl.dataset.original = titleEl.innerHTML;
        if (descEl) descEl.dataset.original = descEl.innerHTML;
    });

    function applyFilters() {
        menuItems.forEach(item => {
            const matchesCategory = (item.dataset.category === currentCategory);
            const matchesDiet = (currentDiet === 'all' || item.dataset.diet === currentDiet);
            
            // For search, we check the item's title (h3) and description (p)
            const titleEl = item.querySelector('h3');
            const descEl = item.querySelector('p.line-clamp-2');
            
            const title = titleEl ? titleEl.textContent.toLowerCase() : '';
            const desc = descEl ? descEl.textContent.toLowerCase() : '';
            const matchesSearch = (title.includes(currentSearch) || desc.includes(currentSearch));

            if (matchesCategory && matchesDiet && matchesSearch) {
                item.style.display = 'block';
                void item.offsetWidth; // Trigger reflow
                item.classList.add('animate-fade-in');
                
                // Highlight text
                if (currentSearch) {
                    // Escape regex to be safe
                    const safeSearch = currentSearch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    const regex = new RegExp(`(${safeSearch})`, 'gi');
                    if (titleEl) {
                        titleEl.innerHTML = titleEl.dataset.original.replace(regex, `<mark class="bg-[#D4AF37] text-black px-1 rounded">$1</mark>`);
                    }
                    if (descEl) {
                        descEl.innerHTML = descEl.dataset.original.replace(regex, `<mark class="bg-[#D4AF37] text-black px-1 rounded">$1</mark>`);
                    }
                } else {
                    if (titleEl) titleEl.innerHTML = titleEl.dataset.original;
                    if (descEl) descEl.innerHTML = descEl.dataset.original;
                }
            } else {
                item.style.display = 'none';
                item.classList.remove('animate-fade-in');
            }
        });
    }

    if (menuSearch) {
        menuSearch.addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase();
            applyFilters();
        });
    }

    if (filterBtns.length > 0 && menuItems.length > 0) {
        // Initialize default category
        if (filterBtns.length > 0) {
            currentCategory = filterBtns[0].dataset.filter;
            filterBtns[0].classList.add('bg-[#D4AF37]', 'text-black', 'font-semibold');
            filterBtns[0].classList.remove('border-gray-600', 'text-gray-300');
        }

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => {
                    b.classList.remove('bg-[#D4AF37]', 'text-black', 'font-semibold');
                    b.classList.add('border-gray-600', 'text-gray-300');
                });
                btn.classList.add('bg-[#D4AF37]', 'text-black', 'font-semibold');
                btn.classList.remove('border-gray-600', 'text-gray-300');

                currentCategory = btn.dataset.filter;
                applyFilters();
            });
        });

        dietBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                dietBtns.forEach(b => {
                    b.classList.remove('bg-[#D4AF37]', 'bg-green-600', 'bg-red-600', 'text-black', 'text-white');
                    // Reset to base border styles based on diet
                    if (b.dataset.diet === 'all') {
                        b.classList.add('text-[#D4AF37]');
                    } else if (b.dataset.diet === 'Veg') {
                        b.classList.add('text-green-500');
                    } else {
                        b.classList.add('text-red-500');
                    }
                });

                // Apply active styles
                if (btn.dataset.diet === 'all') {
                    btn.classList.add('bg-[#D4AF37]', 'text-black');
                    btn.classList.remove('text-[#D4AF37]');
                } else if (btn.dataset.diet === 'Veg') {
                    btn.classList.add('bg-green-600', 'text-white');
                    btn.classList.remove('text-green-500');
                } else if (btn.dataset.diet === 'Non-Veg') {
                    btn.classList.add('bg-red-600', 'text-white');
                    btn.classList.remove('text-red-500');
                }

                currentDiet = btn.dataset.diet;
                applyFilters();
            });
        });
        
        // Initial application
        applyFilters();
    }

    // Admin Dashboard Menu Search
    const adminMenuSearch = document.getElementById('admin-menu-search');
    if (adminMenuSearch) {
        adminMenuSearch.addEventListener('input', function(e) {
            const term = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#admin-menu-table tbody tr');
            rows.forEach(row => {
                // Check if the text in the row matches the search term
                const text = row.textContent.toLowerCase();
                if (text.includes(term)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});
