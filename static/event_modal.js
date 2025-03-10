(function() {
  // Function to open the modal and populate its content
  function openEventModal(el) {
    const overlay = document.getElementById('eventModalOverlay');
    if (!overlay) return;
    
    // Retrieve data attributes from the clicked element
    const title = el.getAttribute('data-title') || "Event Title";
    const date = el.getAttribute('data-date') || "";
    const time = el.getAttribute('data-time') || "";
    const location = el.getAttribute('data-location') || "Location not provided";
    const description = el.getAttribute('data-description') || "";
    const tags = el.getAttribute('data-tags') || "";
    const image = el.getAttribute('data-image') || "";
    
    // Create a message object with the event data
    const message = {
      action: 'openEventModal',
      data: { title, date, time, location, description, tags, image }
    }

    // Update modal elements (make sure these IDs match those in event_detail_fragment.html)
    const modalTitle = document.getElementById('modalEventTitle');
    const modalDescription = document.getElementById('modalEventDescription');
    const modalLocation = document.getElementById('modalEventLocation');
    const modalTags = document.getElementById('modalEventTags');
    const modalImage = document.getElementById('modalEventImage');
    const modalMonth = document.getElementById('modalEventMonth');
    const modalDay = document.getElementById('modalEventDay');

    if (modalTitle) modalTitle.innerText = title;
    if (modalDescription) modalDescription.innerText = description;
    if (modalLocation) modalLocation.innerText = location;
    
    // Update tags (assuming comma-separated)
    if (modalTags) {
      if (tags) {
        modalTags.innerHTML = tags.split(',').map(tag => `<span>${tag.trim()}</span>`).join(' ');
      } else {
        modalTags.innerHTML = "";
      }
    }
    
    // Update the image if provided
    if (modalImage) {
      if (image) {
        modalImage.src = image;
        modalImage.style.display = 'block';
      } else {
        modalImage.style.display = 'none';
      }
    }
    
    // Process the date to update the modal's date block (month and day)
    if (date && modalMonth && modalDay) {
      const d = new Date(date);
      const monthNames = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
      modalMonth.innerText = monthNames[d.getMonth()] || "";
      modalDay.innerText = d.getDate() || "";
    }
    
    // Finally, display the modal overlay
    overlay.style.display = 'flex';
  }

  // Function to close the modal
  function closeEventModal() {
    const overlay = document.getElementById('eventModalOverlay');
    if (overlay) {
      overlay.style.display = 'none';
    }
  }

  // When DOM is loaded, add listeners
  document.addEventListener('DOMContentLoaded', function() {
    // Attach close event listeners for the X button and clicking outside the modal content
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
    
    // Attach event delegation at the document level:
    // Any click on an element (or its child) with the "clickable-event" class will trigger openEventModal.
    document.addEventListener('click', function(e) {
      let target = e.target;
      while (target && target !== document) {
        if (target.classList && target.classList.contains('clickable-event')) {
          console.log("Delegated click on clickable-event", target);
          e.preventDefault();
          openEventModal(target);
          break;
        }
        target = target.parentElement;
      }
    });
  });

  // Expose functions globally (optional)
  window.openEventModal = openEventModal;

  // Post message to the parent window
  window.parent.postMessage(message, '*');
  
  window.CloseEvent = closeEventModal;
})();