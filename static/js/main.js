/**
 * Tugendane - Main JavaScript functions
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Chat form submission
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        initializeChat();
    }

    // Services map
    const servicesMap = document.getElementById('services-map');
    if (servicesMap) {
        // Initialize map when document is ready
        // Initialize map centered on Rwanda
        const map = L.map('services-map').setView([-1.9403, 30.0596], 12);

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Initialize markers for different service types
        const markers = {
            health: [],
            education: [],
            administration: [],
            identification: [],
            taxation: [],
            security: [],
            social: [],
            default: []
        };

        // Fetch services from API
        fetch('/api/services')
            .then(response => response.json())
            .then(data => {
                if (!data.services) {
                    console.error("No services data received");
                    return;
                }

                data.services.forEach(service => {
                    const marker = L.marker([service.latitude, service.longitude])
                        .bindPopup(`
                            <strong>${service.name}</strong><br>
                            Category: ${service.category}<br>
                            Address: ${service.address}<br>
                            ${service.phone_number ? `Phone: ${service.phone_number}<br>` : ''}
                            ${service.opening_hours ? `Hours: ${service.opening_hours}` : ''}
                        `);

                    // Add to category group
                    if (service.category && markers[service.category]) {
                        markers[service.category].push(marker);
                    } else {
                        markers.default.push(marker);
                    }
                });

                // Create layer groups for each category
                const layers = {};
                Object.keys(markers).forEach(category => {
                    if (markers[category].length > 0) {
                        layers[`${category.charAt(0).toUpperCase() + category.slice(1)} Services`] = L.layerGroup(markers[category]);
                    }
                });

                // Add all markers to map initially
                Object.values(layers).forEach(layer => layer.addTo(map));

                // Add layer control
                L.control.layers(null, layers, {collapsed: false}).addTo(map);
            })
            .catch(error => {
                console.error("Error loading services:", error);
            });

        // Add search functionality
        const searchControl = document.getElementById('map-search');
        if (searchControl) {
            const searchInput = searchControl.querySelector('input');
            const searchButton = searchControl.querySelector('button');

            const searchServices = (query) => {
                query = query.toLowerCase();
                let found = false;

                Object.values(markers).flat().forEach(marker => {
                    const popup = marker.getPopup();
                    const content = popup.getContent().toLowerCase();

                    if (content.includes(query)) {
                        marker.openPopup();
                        map.setView(marker.getLatLng(), 15);
                        found = true;
                    }
                });

                return found;
            };

            searchButton.addEventListener('click', () => {
                if (!searchServices(searchInput.value)) {
                    alert('No services found matching your search.');
                }
            });

            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    if (!searchServices(searchInput.value)) {
                        alert('No services found matching your search.');
                    }
                }
            });
        }
    }
});

/**
 * Initialize chat functionality
 */
function initializeChat() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const userIdInput = document.getElementById('user-id');

    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const message = messageInput.value.trim();
        if (message === '') return;

        // Add user message to the chat window
        appendMessage('user', message);

        // Clear input
        messageInput.value = '';

        // Show loading indicator
        appendMessage('system loading', 'Thinking...');

        // Send to server
        const formData = new FormData();
        formData.append('message', message);
        formData.append('user_id', userIdInput.value);

        fetch('/chat/send', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            const loadingMsg = chatMessages.querySelector('.message.loading');
            if (loadingMsg) {
                chatMessages.removeChild(loadingMsg);
            }

            // Update user ID
            if (data.user_id) {
                userIdInput.value = data.user_id;
            }

            // Add response to chat
            appendMessage('system', data.response);

            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            // Remove loading message
            const loadingMsg = chatMessages.querySelector('.message.loading');
            if (loadingMsg) {
                chatMessages.removeChild(loadingMsg);
            }

            // Show error message
            appendMessage('system error', 'Sorry, there was an error processing your request. Please try again.');
        });
    });

    // Function to add message to chat window
    function appendMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', type);

        const iconDiv = document.createElement('div');
        iconDiv.classList.add('message-icon');

        const icon = document.createElement('i');
        if (type === 'user') {
            icon.classList.add('fas', 'fa-user');
        } else if (type.includes('loading')) {
            icon.classList.add('fas', 'fa-spinner', 'fa-spin');
        } else if (type.includes('error')) {
            icon.classList.add('fas', 'fa-exclamation-circle');
        } else {
            icon.classList.add('fas', 'fa-robot');
        }

        iconDiv.appendChild(icon);

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        contentDiv.textContent = content;

        messageDiv.appendChild(iconDiv);
        messageDiv.appendChild(contentDiv);

        chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Add initial system message
    if (chatMessages.children.length === 0) {
        appendMessage('system', 'Hello! I am Tugendane, your Rwanda government services assistant. How can I help you today? You can ask me about finding services, getting directions, opening hours, or required documents.');
    }
}


/**
 * Get user's current location
 */
function getCurrentLocation(callback) {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        position => {
            callback({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            });
        },
        error => {
            console.error('Error getting location:', error);
            alert('Unable to retrieve your location. Please try again or enter your location manually.');
        },
        {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        }
    );
}