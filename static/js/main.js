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
        initializeServicesMap();
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
 * Initialize the services map
 */
function initializeServicesMap() {
    // Wait for OpenStreetMap script to load
    if (typeof L !== 'undefined') {
        loadMap();
    } else {
        // If Leaflet isn't loaded yet, wait and try again
        setTimeout(initializeServicesMap, 500);
        return;
    }

    function loadMap() {
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
            social: []
        };
        
        // Custom icons for different service types
        const icons = {
            health: L.divIcon({
                html: '<i class="fas fa-hospital text-danger fa-2x"></i>',
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            education: L.divIcon({
                html: '<i class="fas fa-graduation-cap text-success fa-2x"></i>',
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            administration: L.divIcon({
                html: '<i class="fas fa-university text-warning fa-2x"></i>',
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            identification: L.divIcon({
                html: '<i class="fas fa-id-card text-primary fa-2x"></i>',
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            taxation: L.divIcon({
                html: '<i class="fas fa-money-bill text-success fa-2x"></i>',
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            security: L.divIcon({
                html: '<i class="fas fa-shield-alt text-info fa-2x"></i>',
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            social: L.divIcon({
                html: '<i class="fas fa-hands-helping text-secondary fa-2x"></i>',
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            default: L.divIcon({
                html: '<i class="fas fa-building text-primary fa-2x"></i>',
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            })
        };
        
        // Fetch service data
        fetch('/api/services')
            .then(response => response.json())
            .then(data => {
                // Create markers for each service
                data.services.forEach(service => {
                    // Use appropriate icon based on category
                    const icon = icons[service.category] || icons.default;
                    
                    // Create marker
                    const marker = L.marker([service.latitude, service.longitude], {
                        icon: icon
                    });
                    
                    // Create popup content
                    let popupContent = `
                        <div class="service-popup">
                            <h5>${service.name}</h5>
                            <p><strong>Category:</strong> ${service.category}</p>
                            <p><strong>Address:</strong> ${service.address}</p>
                    `;
                    
                    if (service.phone_number) {
                        popupContent += `<p><strong>Phone:</strong> ${service.phone_number}</p>`;
                    }
                    
                    if (service.opening_hours) {
                        popupContent += `<p><strong>Hours:</strong> ${service.opening_hours}</p>`;
                    }
                    
                    popupContent += `</div>`;
                    
                    // Add popup to marker
                    marker.bindPopup(popupContent);
                    
                    // Add marker to appropriate category
                    if (markers[service.category]) {
                        markers[service.category].push(marker);
                    } else {
                        markers.default = markers.default || [];
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
                
                // Add search control
                const searchControl = document.getElementById('map-search');
                if (searchControl) {
                    const searchInput = searchControl.querySelector('input');
                    const searchButton = searchControl.querySelector('button');
                    
                    searchButton.addEventListener('click', function() {
                        searchServices(searchInput.value);
                    });
                    
                    searchInput.addEventListener('keypress', function(e) {
                        if (e.key === 'Enter') {
                            searchServices(searchInput.value);
                        }
                    });
                    
                    function searchServices(query) {
                        if (!query) return;
                        
                        query = query.toLowerCase();
                        let found = false;
                        
                        // Search through all services
                        data.services.forEach(service => {
                            if (service.name.toLowerCase().includes(query) || 
                                service.category.toLowerCase().includes(query) ||
                                service.address.toLowerCase().includes(query)) {
                                // Center map on this service
                                map.setView([service.latitude, service.longitude], 15);
                                
                                // Find and open the popup for this marker
                                Object.values(markers).forEach(categoryMarkers => {
                                    categoryMarkers.forEach(marker => {
                                        const latLng = marker.getLatLng();
                                        if (latLng.lat === service.latitude && latLng.lng === service.longitude) {
                                            marker.openPopup();
                                            found = true;
                                        }
                                    });
                                });
                            }
                        });
                        
                        if (!found) {
                            alert('No services found matching your search');
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error loading services:', error);
                document.getElementById('services-map').innerHTML = '<div class="alert alert-danger">Error loading services. Please try again later.</div>';
            });
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
