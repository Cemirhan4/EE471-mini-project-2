/**
 * Voice-Activated Library Inventory — Frontend Controller (EE471 Mini Project #2)
 * Merges Week 4 baseline UI with Azure Cognitive Speech Services
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- DOM Elements ---
  const notificationArea = document.getElementById('notification-area');
  const notificationTitle = document.getElementById('notification-title');
  const notificationMessage = document.getElementById('notification-message');
  const notificationClose = document.getElementById('notification-close');

  const itemForm = document.getElementById('item-form');
  const formSectionTag = document.getElementById('form-section-tag');
  const formTitle = document.getElementById('form-title');
  const formDesc = document.getElementById('form-desc');
  const editItemIdInput = document.getElementById('edit-item-id');
  const itemTitleInput = document.getElementById('item-title');
  const itemAuthorInput = document.getElementById('item-author');
  const itemMetricInput = document.getElementById('item-metric');
  const metricLabel = document.getElementById('metric-label');
  const metricSuffix = document.getElementById('metric-suffix');
  const submitBtnText = document.getElementById('submit-btn-text');
  const cancelEditBtn = document.getElementById('cancel-edit-btn');
  const typeSelector = document.getElementById('type-selector');

  const itemsListContainer = document.getElementById('items-list');
  const itemCountSpan = document.getElementById('item-count');
  const filterTabs = document.querySelectorAll('.filter-tab');
  const availableToggle = document.getElementById('available-toggle');

  // Voice Hub Elements
  const micBtn = document.getElementById('mic-btn');
  const voiceBadge = document.getElementById('voice-badge');
  const voiceCaption = document.getElementById('voice-caption');
  const voiceBubble = document.getElementById('voice-bubble');
  const bubbleUserText = document.getElementById('bubble-user-text');
  const bubbleLibrarianText = document.getElementById('bubble-librarian-text');
  const librarianAudio = document.getElementById('librarian-audio');

  // --- State ---
  let selectedType = 'book';
  let activeFilterType = 'all';
  let filterAvailableOnly = false;
  let notificationTimer = null;
  let isListening = false;
  let recognition = null;

  // ==========================================================================
  // NOTIFICATIONS (Requirement #2)
  // ==========================================================================
  function showNotification(title, message, isError = true) {
    if (notificationTimer) clearTimeout(notificationTimer);

    notificationArea.className = `notification-area ${isError ? 'error' : 'success'}`;
    const icon = isError ? '⚠️' : '✅';
    document.getElementById('notification-icon').textContent = icon;
    notificationTitle.textContent = title;
    notificationMessage.textContent = message;
    notificationArea.style.display = 'flex';

    notificationTimer = setTimeout(() => {
      hideNotification();
    }, 6000);
  }

  function hideNotification() {
    notificationArea.style.display = 'none';
    if (notificationTimer) clearTimeout(notificationTimer);
  }

  notificationClose.addEventListener('click', hideNotification);

  // ==========================================================================
  // FORM TYPE SELECTOR (Book vs DVD)
  // ==========================================================================
  typeSelector.querySelectorAll('.segment').forEach(btn => {
    btn.addEventListener('click', () => {
      if (editItemIdInput.value) return; // type is immutable on PUT
      typeSelector.querySelectorAll('.segment').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedType = btn.dataset.type;
      updateMetricLabels();
    });
  });

  function updateMetricLabels() {
    if (selectedType === 'book') {
      metricLabel.textContent = 'Page count';
      metricSuffix.textContent = 'pages';
      itemMetricInput.placeholder = '320';
    } else {
      metricLabel.textContent = 'Duration';
      metricSuffix.textContent = 'mins';
      itemMetricInput.placeholder = '120';
    }
  }

  // ==========================================================================
  // FETCH & RENDER ITEMS
  // ==========================================================================
  async function fetchItems() {
    try {
      const params = new URLSearchParams();
      if (filterAvailableOnly) {
        params.append('available', 'true');
      }
      if (activeFilterType !== 'all') {
        params.append('type', activeFilterType);
      }

      const queryString = params.toString() ? `?${params.toString()}` : '';
      const response = await fetch(`/api/items${queryString}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        showNotification('Error', errorData.error || 'Failed to fetch items');
        return;
      }

      const items = await response.json();
      renderItems(items);
    } catch (err) {
      showNotification('Network Error', 'Could not reach server: ' + err.message);
    }
  }

  function renderItems(items) {
    itemCountSpan.textContent = items.length;

    if (items.length === 0) {
      itemsListContainer.innerHTML = `
        <div class="empty-state">
          No items found matching the selected filters.
        </div>
      `;
      return;
    }

    itemsListContainer.innerHTML = '';
    items.forEach(item => {
      const card = createItemCard(item);
      itemsListContainer.appendChild(card);
    });
  }

  function createItemCard(item) {
    const card = document.createElement('div');
    card.className = 'item-card';
    card.dataset.id = item.id;

    const isBook = item.type === 'Book';
    const isAvail = item.is_available;
    const thumbClass = isBook ? 'book-thumb' : 'dvd-thumb';
    const metricText = isBook ? `${item.page_count} pages` : `${item.duration} mins`;
    const statusClass = isAvail ? 'available' : 'checked-out';
    const statusText = isAvail ? 'Available' : 'Checked out';

    // SVG Thumbnails
    const iconSvg = isBook
      ? `<svg class="thumb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
        </svg>`
      : `<svg class="thumb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <circle cx="12" cy="12" r="3"></circle>
        </svg>`;

    // Action button
    const actionBtn = isAvail
      ? `<button class="btn-action btn-checkout" data-action="checkout" data-id="${item.id}">Checkout</button>`
      : `<button class="btn-action btn-return" data-action="return" data-id="${item.id}">Return</button>`;

    card.innerHTML = `
      <div class="item-thumb ${thumbClass}">
        ${iconSvg}
      </div>

      <div class="item-info">
        <h3 class="item-title">${escapeHtml(item.title)}</h3>
        <p class="item-author">${escapeHtml(item.author)}</p>
        <span class="item-meta">${item.type} &bull; ${metricText}</span>
      </div>

      <div class="status-pill ${statusClass}">
        <span class="dot"></span>
        <span>${statusText}</span>
      </div>

      <div class="item-actions">
        ${actionBtn}
        <button class="btn-icon btn-edit" title="Edit item" data-id="${item.id}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20h9"></path>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
          </svg>
        </button>
        <button class="btn-icon btn-delete" title="Delete item" data-id="${item.id}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `;

    // Event Listeners on Card
    card.querySelector('[data-action="checkout"]')?.addEventListener('click', () => checkoutItem(item.id));
    card.querySelector('[data-action="return"]')?.addEventListener('click', () => returnItem(item.id));
    card.querySelector('.btn-edit').addEventListener('click', () => enterEditMode(item));
    card.querySelector('.btn-delete').addEventListener('click', () => deleteItem(item.id));

    return card;
  }

  // ==========================================================================
  // ACTIONS: CHECKOUT, RETURN, DELETE, CREATE/EDIT
  // ==========================================================================
  async function checkoutItem(id) {
    try {
      const res = await fetch(`/api/items/${id}/checkout`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        showNotification('Checkout Failed (409/404)', data.error, true);
        speakVoice(`Sorry, item ${id} is already checked out.`);
      } else {
        showNotification('Item Checked Out', data.message, false);
        speakVoice(`Item ${id}, '${data.item.title}', has been checked out.`);
        fetchItems();
      }
    } catch (err) {
      showNotification('Error', err.message, true);
    }
  }

  async function returnItem(id) {
    try {
      const res = await fetch(`/api/items/${id}/return`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        showNotification('Return Failed (409/404)', data.error, true);
        speakVoice(`Sorry, item ${id} is not currently checked out.`);
      } else {
        showNotification('Item Returned', data.message, false);
        speakVoice(`Item ${id}, '${data.item.title}', has been returned.`);
        fetchItems();
      }
    } catch (err) {
      showNotification('Error', err.message, true);
    }
  }

  async function deleteItem(id) {
    if (!confirm(`Are you sure you want to remove item #${id}?`)) return;

    try {
      const res = await fetch(`/api/items/${id}`, { method: 'DELETE' });
      if (res.status === 204) {
        showNotification('Item Removed', `Item #${id} removed from inventory.`, false);
        speakVoice(`Item ${id} has been removed from the library.`);
        fetchItems();
      } else {
        const data = await res.json().catch(() => ({}));
        showNotification('Delete Blocked (409/404)', data.error || 'Failed to delete item.', true);
        speakVoice(data.error || 'Delete failed.');
      }
    } catch (err) {
      showNotification('Error', err.message, true);
    }
  }

  function enterEditMode(item) {
    editItemIdInput.value = item.id;
    itemTitleInput.value = item.title;
    itemAuthorInput.value = item.author;

    selectedType = item.type.toLowerCase();
    typeSelector.querySelectorAll('.segment').forEach(b => {
      b.classList.toggle('active', b.dataset.type === selectedType);
      b.disabled = true; // type immutable on PUT
    });

    if (selectedType === 'book') {
      itemMetricInput.value = item.page_count;
    } else {
      itemMetricInput.value = item.duration;
    }
    updateMetricLabels();

    formSectionTag.textContent = 'EDIT RECORD';
    formTitle.textContent = `Edit item #${item.id}`;
    formDesc.textContent = 'Update the fields below and save your changes.';
    submitBtnText.textContent = 'Save changes';
    cancelEditBtn.style.display = 'inline-flex';

    itemTitleInput.focus();
  }

  function exitEditMode() {
    editItemIdInput.value = '';
    itemForm.reset();
    selectedType = 'book';
    typeSelector.querySelectorAll('.segment').forEach(b => {
      b.classList.toggle('active', b.dataset.type === 'book');
      b.disabled = false;
    });
    updateMetricLabels();

    formSectionTag.textContent = 'NEW RECORD';
    formTitle.textContent = 'Add an item';
    formDesc.textContent = 'Enter the details below to add it to the collection.';
    submitBtnText.textContent = 'Add to library';
    cancelEditBtn.style.display = 'none';
  }

  cancelEditBtn.addEventListener('click', exitEditMode);

  itemForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const isEdit = !!editItemIdInput.value;
    const itemId = editItemIdInput.value;
    const title = itemTitleInput.value.trim();
    const author = itemAuthorInput.value.trim();
    const metricVal = parseInt(itemMetricInput.value, 10);

    const payload = {
      title: title,
      author: author,
      type: selectedType
    };

    if (selectedType === 'book') {
      payload.page_count = metricVal;
    } else {
      payload.duration = metricVal;
    }

    try {
      const url = isEdit ? `/api/items/${itemId}` : '/api/items';
      const method = isEdit ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        showNotification(isEdit ? 'Update Failed' : 'Creation Failed', data.error, true);
      } else {
        showNotification(
          isEdit ? 'Item Updated' : 'Item Added',
          isEdit ? `Updated #${data.id} "${data.title}"` : `Added #${data.id} "${data.title}"`,
          false
        );
        const voiceMsg = isEdit 
          ? `Item ${data.id} has been updated.`
          : `Successfully created ${selectedType} '${data.title}' with ID ${data.id}.`;
        speakVoice(voiceMsg);
        exitEditMode();
        fetchItems();
      }
    } catch (err) {
      showNotification('Error', err.message, true);
    }
  });

  // Filter Tabs
  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeFilterType = tab.dataset.filterType;
      fetchItems();
    });
  });

  // Available Toggle
  availableToggle.addEventListener('change', (e) => {
    filterAvailableOnly = e.target.checked;
    fetchItems();
  });

  // ==========================================================================
  // VOICE ACTIVATION (Azure Speech Services)
  // ==========================================================================
  function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      voiceCaption.innerHTML = 'Speech API not supported in browser. Use <strong>Quick Voice Commands</strong>!';
      return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      isListening = true;
      micBtn.classList.add('listening');
      voiceBadge.textContent = 'Listening...';
      voiceBadge.classList.add('listening');
      voiceCaption.textContent = 'Speak your library command now...';
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      processVoiceCommand(transcript);
    };

    recognition.onerror = (event) => {
      stopListening();
      showNotification('Speech Error', event.error, true);
    };

    recognition.onend = () => {
      stopListening();
    };
  }

  function toggleListening() {
    if (!recognition) {
      alert('Speech recognition is supported in Chrome/Edge browsers. You can also use the one-click command buttons below!');
      return;
    }
    if (isListening) {
      recognition.stop();
    } else {
      recognition.start();
    }
  }

  function stopListening() {
    isListening = false;
    micBtn.classList.remove('listening');
    voiceBadge.textContent = 'Ready to Listen';
    voiceBadge.classList.remove('listening');
    voiceCaption.innerHTML = 'Click mic or say <em>"Check out item 1"</em>';
  }

  micBtn.addEventListener('click', toggleListening);

  async function processVoiceCommand(spokenText) {
    voiceBubble.style.display = 'flex';
    bubbleUserText.textContent = `"${spokenText}"`;
    bubbleLibrarianText.textContent = 'Processing request...';

    try {
      const res = await fetch('/api/voice/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: spokenText })
      });

      const data = await res.json();
      bubbleLibrarianText.textContent = data.librarian_response;

      // Play synthesized Azure voice
      if (data.audio_url) {
        librarianAudio.src = `${data.audio_url}?t=${Date.now()}`;
        librarianAudio.play().catch(e => console.log('Audio autoplay prevented:', e));
      } else {
        speakBrowserVoice(data.librarian_response);
      }

      // Sync UI filters if list command was invoked
      if (data.details && data.details.action === 'list' && data.details.filter) {
        const f = data.details.filter;
        if (f.available !== null && f.available !== undefined) {
          availableToggle.checked = f.available;
          filterAvailableOnly = f.available;
        }
        if (f.type) {
          filterTabs.forEach(t => {
            t.classList.toggle('active', t.dataset.filterType === f.type);
          });
          activeFilterType = f.type;
        }
      }

      showNotification(
        data.success ? 'Voice Command Executed' : 'Voice Command Notice',
        data.librarian_response,
        !data.success
      );

      fetchItems();
    } catch (err) {
      bubbleLibrarianText.textContent = `Error: ${err.message}`;
      showNotification('Voice Error', err.message, true);
    }
  }

  // Global shortcut function for one-click test buttons
  window.triggerVoiceShortcut = function(text) {
    processVoiceCommand(text);
  };

  function speakVoice(text) {
    voiceBubble.style.display = 'flex';
    bubbleLibrarianText.textContent = text;
    speakBrowserVoice(text);
  }

  function speakBrowserVoice(text) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = 'en-US';
      window.speechSynthesis.speak(u);
    }
  }

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  // Initial setup
  updateMetricLabels();
  initSpeechRecognition();
  fetchItems();
});
