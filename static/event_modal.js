(function() {
  function openEventModal(el) {
    const overlay = document.getElementById('eventModalOverlay');
    if (!overlay) return;
  
    // Retrieve data attributes from the clicked element
    const title = el.getAttribute('data-title') || "Event Title";
    const date = el.getAttribute('data-date') || "";
    const location = el.getAttribute('data-location') || "Location not provided";
    const organizer = el.getAttribute('data-organizer') || "Organizer not provided";
    const description = el.getAttribute('data-description') || "";
  
    // Update modal elements
    const modalTitle = document.getElementById('modalEventTitle');
    const modalDescription = document.getElementById('modalEventDescription');
    const modalLocation = document.getElementById('modalEventLocation');
    const modalOrganizer = document.getElementById('modalEventOrganizer');
    const modalMonth = document.getElementById('modalEventMonth');
    const modalDay = document.getElementById('modalEventDay');
  
    if (modalTitle) modalTitle.innerText = title;
    if (modalDescription) modalDescription.innerText = description;
    if (modalLocation) modalLocation.innerText = location;
  
    // Build extra hyperlink if organizer matches one of the conditions
    let extraLink = "";
    if (organizer === "Sanctus") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/young-adult-ministry/" target="_blank">Sanctus Website</a>';
    } else if (organizer === "BTYM") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/youth-ministry/" target="_blank">BTYM Website</a>';
    } else if (organizer.toLowerCase() === "women\'s ministry") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/womens-ministry/" target="_blank">The Exchange Website</a>';
    } else if (organizer.startsWith("BT Kids")) {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/childrens-ministry/" target="_blank">BT Kids Website</a>';
    } else if (organizer.toLowerCase() === "men\'s ministry") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/mens-ministry/" target="_blank">Men\'s Website</a>';
    } else if (organizer === "Marriage Ministry") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/marriage-ministry/" target="_blank">Marriage Website</a>';
    } else if (organizer === "Global Missions") {
      extraLink = '<br/><a href="https://www.brooklyntabernacle.org/connect/global-missions/" target="_blank">Global Missions Website</a>';
    }
  
    if (modalOrganizer) {
      modalOrganizer.innerHTML = organizer + extraLink;
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
  
  function closeEventModal() {
    const overlay = document.getElementById('eventModalOverlay');
    if (overlay) {
      overlay.style.display = 'none';
    }
  }
  
  document.addEventListener('DOMContentLoaded', function() {
    // Attach close event listeners
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
  
    // Event delegation: any click on an element with class "clickable-event" triggers the modal
    document.addEventListener('click', function(e) {
      let target = e.target;
      while (target && target !== document) {
        if (target.classList && target.classList.contains('clickable-event')) {
          e.preventDefault();
          openEventModal(target);
          break;
        }
        target = target.parentElement;
      }
    });
  });
  
  window.openEventModal = openEventModal;
  window.CloseEvent = closeEventModal;
})();