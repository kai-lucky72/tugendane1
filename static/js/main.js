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
        initMap();
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


// Initialize map and markers
let map;
let markers = [];
let userMarker;

function initMap() {
    // Center on Rwanda
    const rwanda = [-1.9403, 29.8739];

    map = L.map('services-map').setView(rwanda, 8);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Get user's location
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {
            const userLat = position.coords.latitude;
            const userLng = position.coords.longitude;

            // Add user marker
            if (userMarker) {
                userMarker.setLatLng([userLat, userLng]);
            } else {
                userMarker = L.marker([userLat, userLng], {
                    icon: L.divIcon({
                        className: 'user-location',
                        html: '<i class="fas fa-user-circle"></i>'
                    })
                }).addTo(map);
            }

            // Center map on user
            map.setView([userLat, userLng], 12);

            // Load services near user location
            loadServices(userLat, userLng);
        });
    }
}

function loadServices(lat, lng) {
    fetch('/api/services?lat=' + lat + '&lng=' + lng)
        .then(response => response.json())
        .then(data => {
            if (data.services) {
                // Clear existing markers
                markers.forEach(marker => marker.remove());
                markers = [];

                // Add service markers
                data.services.forEach(service => {
                    const marker = L.marker([service.latitude, service.longitude])
                        .bindPopup(`
                            <h5>${service.name}</h5>
                            <p>${service.address}</p>
                            ${service.phone_number ? `<p>📞 ${service.phone_number}</p>` : ''}
                            ${service.opening_hours ? `<p>⏰ ${service.opening_hours}</p>` : ''}
                        `);
                    marker.addTo(map);
                    markers.push(marker);
                });
            } else {
                console.log("No services data received");
            }
        })
        .catch(err => {
            console.log("Error loading services:", err);
        });
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