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


// MapBox access token (using public token for demo)
const mapboxToken = 'pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw';

let map;
let userMarker;
let serviceMarkers = [];

function initMap() {
    if (map) {
        map.remove();
    }

    // Initialize map centered on Rwanda
    map = L.map('services-map').setView([-1.9403, 29.8739], 8);

    // Use MapBox tiles for better detail
    L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token=' + mapboxToken, {
        attribution: '© MapBox | © OpenStreetMap',
        id: 'mapbox/streets-v11',
        tileSize: 512,
        zoomOffset: -1
    }).addTo(map);

    // Get user's location with high accuracy
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const userLat = position.coords.latitude;
                const userLng = position.coords.longitude;

                // Add/update user marker
                if (userMarker) {
                    userMarker.setLatLng([userLat, userLng]);
                } else {
                    userMarker = L.marker([userLat, userLng], {
                        icon: L.divIcon({
                            className: 'user-location',
                            html: '<i class="fas fa-user-circle fa-2x text-primary"></i>'
                        })
                    }).addTo(map);
                }

                // Add user popup
                userMarker.bindPopup('Your Location').openPopup();

                // Center map on user
                map.setView([userLat, userLng], 13);

                // Load services near user location
                loadServices(userLat, userLng);
            },
            function(error) {
                console.error("Error getting location:", error);
                // Load default services for Rwanda if location fails
                loadServices(-1.9403, 29.8739);
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }
        );
    }
}

function loadServices(lat, lng) {
    // Clear existing markers
    serviceMarkers.forEach(marker => marker.remove());
    serviceMarkers = [];

    fetch(`/api/services?lat=${lat}&lng=${lng}`)
        .then(response => response.json())
        .then(data => {
            if (data.services && data.services.length > 0) {
                data.services.forEach(service => {
                    // Create marker for service
                    const marker = L.marker([service.latitude, service.longitude], {
                        icon: L.divIcon({
                            className: `service-location ${service.category}`,
                            html: getServiceIcon(service.category)
                        })
                    }).addTo(map);

                    // Add popup with service info
                    const popupContent = `
                        <div class="service-popup">
                            <h5>${service.name}</h5>
                            <p><strong>Category:</strong> ${service.category}</p>
                            <p><strong>Address:</strong> ${service.address}</p>
                            <p><strong>Hours:</strong> ${service.opening_hours || 'N/A'}</p>
                            <p><strong>Phone:</strong> ${service.phone_number || 'N/A'}</p>
                            <button onclick="getDirections(${service.latitude}, ${service.longitude})" class="btn btn-sm btn-primary">Get Directions</button>
                        </div>
                    `;
                    marker.bindPopup(popupContent);
                    serviceMarkers.push(marker);
                });
            } else {
                console.warn("No services data received");
            }
        })
        .catch(error => {
            console.error("Error loading services:", error);
        });
}

function getServiceIcon(category) {
    const icons = {
        'health': '<i class="fas fa-hospital fa-lg text-danger"></i>',
        'education': '<i class="fas fa-school fa-lg text-success"></i>',
        'government': '<i class="fas fa-building fa-lg text-primary"></i>',
        'social': '<i class="fas fa-users fa-lg text-info"></i>',
        'default': '<i class="fas fa-map-marker-alt fa-lg text-secondary"></i>'
    };
    return icons[category] || icons.default;
}

function getDirections(lat, lng) {
    if (userMarker) {
        const userLat = userMarker.getLatLng().lat;
        const userLng = userMarker.getLatLng().lng;

        // Send SMS for directions
        fetch('/api/request_directions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                from_lat: userLat,
                from_lng: userLng,
                to_lat: lat,
                to_lng: lng
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Directions have been sent to your phone!");
            }
        })
        .catch(error => console.error("Error requesting directions:", error));
    }
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', initMap);