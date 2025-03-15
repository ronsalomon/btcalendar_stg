(function() {
  // Helper function to clean description HTML by removing image containers
  function cleanDescription(descriptionHtml) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = descriptionHtml;
    
    // Remove image containers with class ai1ec-event-avatar or timely
    const imageContainers = tempDiv.querySelectorAll('.ai1ec-event-avatar, .timely');
    imageContainers.forEach(container => {
      container.remove();
    });
    
    return tempDiv.innerHTML;
  }

  function openEventModalImpl(el) {
    const overlay = document.getElementById('eventModalOverlay');
    if (!overlay) return;
  
    // Retrieve data attributes from the clicked element
    const title = el.getAttribute('data-title') || "Event Title";
    const date = el.getAttribute('data-date') || "";
    const time = el.getAttribute('data-time') || "";
    const location = el.getAttribute('data-location') || "Location not provided";
    const organizer = el.getAttribute('data-organizer') || "Organizer not provided";
    const description = el.getAttribute('data-description') || "";
    const image = el.getAttribute('data-image') || "";
    const registration = el.getAttribute('data-registration') || "";
  
    // Debug output for image
    console.log("Event image URL:", image);
  
    // Update modal elements
    const modalTitle = document.getElementById('modalEventTitle');
    const modalDescription = document.getElementById('modalEventDescription');
    const modalLocation = document.getElementById('modalEventLocation');
    const modalOrganizer = document.getElementById('modalEventOrganizer');
    const modalImage = document.getElementById('modalEventImage');
    const modalMonth = document.getElementById('modalEventMonth');
    const modalDay = document.getElementById('modalEventDay');
    const modalRegister = document.getElementById('modalEventRegister');

    // NEW: references to bottom "Date" & "Time" lines in modal body
    const modalEventDate = document.getElementById('modalEventDate');
    const modalEventTime = document.getElementById('modalEventTime');
  
    // Title
    if (modalTitle) {
      modalTitle.innerText = title;
    }
    // Clean + set description
    if (modalDescription) {
      modalDescription.innerHTML = cleanDescription(description);
    }
    // Location
    if (modalLocation) {
      modalLocation.innerText = location;
    }
  
    // Build extra hyperlink for Organizer if applicable
    let extraLink = "";
    if (organizer === "Sanctus") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/young-adult-ministry/" target="_blank">Sanctus Website</a>';
    } else if (organizer === "BTYM") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/youth-ministry/" target="_blank">BTYM Website</a>';
    } else if (organizer.toLowerCase() === "women's ministry") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/womens-ministry/" target="_blank">The Exchange Website</a>';
    } else if (organizer.startsWith("BT Kids")) {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/childrens-ministry/" target="_blank">BT Kids Website</a>';
    } else if (organizer.toLowerCase() === "men's ministry") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/mens-ministry/" target="_blank">Men\'s Website</a>';
    } else if (organizer === "Marriage Ministry") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/marriage-ministry/" target="_blank">Marriage Website</a>';
    } else if (organizer === "Global Missions") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/global-missions/" target="_blank">Global Missions Website</a>';
    }
  
    if (modalOrganizer) {
      modalOrganizer.innerHTML = organizer + extraLink;
    }
  
    // Set the modal image if provided
    if (modalImage) {
      if (image && image.trim() !== "") {
        console.log("Setting image src to:", image);
        modalImage.src = image;
        modalImage.style.display = 'block';
      } else {
        console.log("No image provided, hiding image element");
        modalImage.style.display = 'none';
      }
    }
  
    // Update the registration button if registration is provided.
    if (modalRegister) {
      if (registration.trim() !== "") {
        // You could also set the href if needed
        modalRegister.innerHTML = '<a href="#" class="register-button">Register</a>';
      } else {
        modalRegister.innerHTML = ""; 
      }
    }
  
    // Process the date to update the top date block (Month and Day)
    if (date && modalMonth && modalDay) {
      const d = new Date(date);
      const monthNames = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
      modalMonth.innerText = monthNames[d.getMonth()] || "";
      modalDay.innerText = d.getDate() || "";
    }

    // -- NEW: Also set the bottom Date & Time lines in modal body --
    // "Date" line (e.g. "Mar 4, 2025")
    if (modalEventDate && date) {
      const d = new Date(date);
      modalEventDate.innerText = d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric"
      });
    }

    // "Time" line (convert "HH:MM" to "h:MM AM/PM")
    if (modalEventTime && time) {
      try {
        let [h, m] = time.split(":");
        let hours = parseInt(h, 10);
        let minutes = parseInt(m, 10) || 0;
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        if (hours === 0) hours = 12;
        modalEventTime.innerText = `${hours}:${minutes.toString().padStart(2,'0')} ${ampm}`;
      } catch (err) {
        console.error("Error formatting time:", err);
        modalEventTime.innerText = time; // fallback
      }
    }
  
    // Finally, display the modal overlay
    overlay.style.display = 'flex';
  }
  
  function closeEventModal() {
    const overlay = document.getElementById('eventModalOverlay');
    if (overlay) {
      overlay.style.display = 'none';
    }
  }
  
  function getDirections() {
    const modalLocation = document.getElementById('modalEventLocation');
    if (!modalLocation) return;
    
    const destinationAddress = modalLocation.innerText + ", Brooklyn, NY 11201";
    const destination = encodeURIComponent(destinationAddress);
  
    const openDirections = (origin) => {
      let originParam = "";
      if (origin) {
        originParam = `&origin=${encodeURIComponent(origin)}`;
      }
      const url = `https://www.google.com/maps/dir/?api=1${originParam}&destination=${destination}`;
      window.open(url, "_blank");
    };
  
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const origin = position.coords.latitude + "," + position.coords.longitude;
          openDirections(origin);
        },
        (error) => {
          openDirections(null);
        }
      );
    } else {
      openDirections(null);
    }
  }
  
  document.addEventListener('DOMContentLoaded', function() {
    const closeBtn = document.getElementById('closeEventModalBtn');
    const overlay = document.getElementById('eventModalOverlay');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeEventModal);
    }
    if (overlay) {
      overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
          closeEventModal();
        }
      });
    }
  
    document.addEventListener('click', function(e) {
      let target = e.target;
      while (target && target !== document) {
        if (target.classList && target.classList.contains('clickable-event')) {
          e.preventDefault();
          openEventModalImpl(target);
          break;
        }
        target = target.parentElement;
      }
    });
  });
  
  // Make functions available globally
  window.openEventModal = openEventModalImpl;
  window.CloseEvent = closeEventModal;
  window.getDirections = getDirections;
})();