/*
=========================================================
 TALKBRIDGE 2.0
 Frontend Application Logic
=========================================================

 LOCAL BACKEND:
 http://127.0.0.1:8000

 DEPLOYED BACKEND:
 https://talkbridge-api.onrender.com

 Change API_BASE_URL when switching between local and
 deployed backend.

 Never put your OpenAI API key in this file.
=========================================================
*/

const API_BASE_URL = "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);

/* =======================================================
   LANGUAGES
======================================================= */

const LANGUAGES = [
  "Auto Detect",
  "English",
  "Twi",
  "Ewe",
  "Ga",
  "Dagbani",
  "Fante",
  "French",
  "Spanish",
  "German",
  "Chinese",
  "Arabic",
  "Japanese",
  "Korean",
  "Portuguese",
  "Hindi",
  "Italian",
  "Russian",
  "Dutch",
  "Turkish",
  "Swedish",
  "Polish"
];

/* =======================================================
   LOCAL STORAGE
======================================================= */

const STORAGE_KEYS = {
  history: "talkbridge_history_v2",
  saved: "talkbridge_saved_v2",
  preferences: "talkbridge_preferences_v2"
};

const DEFAULT_PREFERENCES = {
  source: "Auto Detect",
  target: "Twi",
  autoplay: true,
  speed: 1
};

let preferences = loadStorage(
  STORAGE_KEYS.preferences,
  DEFAULT_PREFERENCES
);

let historyItems = loadStorage(STORAGE_KEYS.history, []);
let savedItems = loadStorage(STORAGE_KEYS.saved, []);

/* =======================================================
   APPLICATION STATE
======================================================= */

let selectedImageFile = null;
let selectedDocumentFile = null;
let selectedSpeechFile = null;

let translationRecorder = null;
let speechRecorder = null;
let conversationRecorder = null;

let translationStream = null;
let speechStream = null;
let conversationStream = null;

let translationChunks = [];
let speechChunks = [];
let conversationChunks = [];

let lastTranslation = null;
let lastImageResult = null;
let lastWritingResult = null;
let lastDocumentResult = null;
let lastTranscript = null;
let lastConversation = null;

let documentAudioBlob = null;
let documentAudioUrl = null;
let conversationAudioUrl = null;
let imagePreviewUrl = null;
let toastTimer = null;

/* =======================================================
   STORAGE HELPERS
======================================================= */

function loadStorage(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch (error) {
    console.warn("Could not read browser storage:", error);
    return fallback;
  }
}

function saveStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error("Could not save browser data:", error);
    showToast("Browser storage is full. Some data could not be saved.");
  }
}

/* =======================================================
   GENERAL HELPERS
======================================================= */

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[char]);
}

function showToast(message) {
  const toast = $("toast");

  if (!toast) {
    console.log(message);
    return;
  }

  toast.textContent = message;
  toast.classList.add("show");

  clearTimeout(toastTimer);

  toastTimer = setTimeout(() => {
    toast.classList.remove("show");
  }, 3000);
}

function setBusy(
  active,
  title = "Working on it...",
  message = "Please wait."
) {
  const overlay = $("busyOverlay");

  if (!overlay) return;

  overlay.classList.toggle("hidden", !active);

  $("busyTitle").textContent = title;
  $("busyMessage").textContent = message;
}

function setButtonLoading(button, loading, originalText) {
  if (!button) return;

  button.disabled = loading;

  if (loading) {
    button.dataset.originalText = button.textContent;
    button.textContent = "Please wait...";
  } else {
    button.textContent =
      originalText ||
      button.dataset.originalText ||
      "Submit";
  }
}

function formatDate(date) {
  return new Date(date).toLocaleString();
}

function makeId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/* =======================================================
   API REQUEST HANDLER
======================================================= */

async function api(path, options = {}) {
  const base = API_BASE_URL.replace(/\/+$/, "");
  const endpoint = path.replace(/^\/+/, "");

  const url = `${base}/${endpoint}`;

  let response;

  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(
      "Cannot connect to TalkBridge backend. Make sure the FastAPI server is running and the API address is correct."
    );
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;

    try {
      const data = await response.json();

      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail
          .map(item => item.msg || JSON.stringify(item))
          .join(", ");
      } else if (data.message) {
        message = data.message;
      }
    } catch {
      try {
        message = await response.text() || message;
      } catch {
        // Keep the original error message.
      }
    }

    throw new Error(message);
  }

  const contentType =
    response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.blob();
}

/* =======================================================
   HISTORY AND SAVED RESULTS
======================================================= */

function addHistory(type, title, content, metadata = {}) {
  const item = {
    id: makeId(),
    type,
    title,
    content: String(content ?? ""),
    metadata,
    createdAt: new Date().toISOString()
  };

  historyItems.unshift(item);

  // Keep the latest 200 activities.
  historyItems = historyItems.slice(0, 200);

  saveStorage(STORAGE_KEYS.history, historyItems);

  renderHistory();
  renderRecent();

  return item;
}

function saveResult(type, title, content, metadata = {}) {
  if (!String(content || "").trim()) {
    showToast("There is no result to save.");
    return;
  }

  const item = {
    id: makeId(),
    type,
    title,
    content: String(content),
    metadata,
    createdAt: new Date().toISOString()
  };

  savedItems.unshift(item);

  saveStorage(STORAGE_KEYS.saved, savedItems);

  renderSaved();

  showToast("Result saved successfully.");
}

function getIcon(type) {
  const icons = {
    translation: "⇄",
    image: "▧",
    writing: "✎",
    document: "▤",
    speech: "♫",
    conversation: "♫"
  };

  return icons[type] || "•";
}

function renderActivityItem(item, saved = false) {
  return `
    <article class="activity-item">

      <div class="activity-icon">
        ${getIcon(item.type)}
      </div>

      <div class="activity-body">

        <strong>${escapeHTML(item.title)}</strong>

        <p>
          ${escapeHTML(item.content.slice(0, 220))}
          ${item.content.length > 220 ? "..." : ""}
        </p>

        <div class="activity-meta">
          ${escapeHTML(formatDate(item.createdAt))}
        </div>

        <div class="activity-actions">

          <button
            class="text-button"
            data-action="open"
            data-id="${escapeHTML(item.id)}"
            data-saved="${saved}">
            View
          </button>

          <button
            class="text-button"
            data-action="copy"
            data-id="${escapeHTML(item.id)}"
            data-saved="${saved}">
            Copy
          </button>

          ${
            saved
              ? `
                <button
                  class="text-button"
                  data-action="delete"
                  data-id="${escapeHTML(item.id)}"
                  data-saved="true">
                  Remove
                </button>
              `
              : ""
          }

        </div>

      </div>

    </article>
  `;
}

function renderHistory() {
  const container = $("historyList");

  if (!container) return;

  if (!historyItems.length) {
    container.innerHTML =
      '<div class="empty-state">No activity yet.</div>';
    return;
  }

  container.innerHTML = historyItems
    .map(item => renderActivityItem(item))
    .join("");
}

function renderSaved() {
  const container = $("savedList");

  if (!container) return;

  if (!savedItems.length) {
    container.innerHTML =
      "<div class=\"empty-state\">You haven't saved anything yet.</div>";
    return;
  }

  container.innerHTML = savedItems
    .map(item => renderActivityItem(item, true))
    .join("");
}

function renderRecent() {
  const container = $("overviewRecent");

  if (!container) return;

  if (!historyItems.length) {
    container.innerHTML =
      '<div class="empty-state">Your recent activities will appear here.</div>';
    return;
  }

  container.innerHTML = historyItems
    .slice(0, 4)
    .map(item => `
      <article class="activity-item">

        <div class="activity-icon">
          ${getIcon(item.type)}
        </div>

        <div class="activity-body">

          <strong>${escapeHTML(item.title)}</strong>

          <p>${escapeHTML(item.content.slice(0, 100))}</p>

          <div class="activity-meta">
            ${escapeHTML(formatDate(item.createdAt))}
          </div>

        </div>

      </article>
    `)
    .join("");
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast("Copied to clipboard.");
  } catch {
    const textarea = document.createElement("textarea");

    textarea.value = text;

    document.body.appendChild(textarea);

    textarea.select();
    document.execCommand("copy");

    textarea.remove();

    showToast("Copied to clipboard.");
  }
}

function openActivity(item) {
  const win = window.open("", "_blank");

  if (!win) {
    showToast("Allow pop-ups to view this result.");
    return;
  }

  const safeTitle = escapeHTML(item.title);
  const safeContent = escapeHTML(item.content);

  win.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${safeTitle} | TalkBridge</title>

      <meta
        name="viewport"
        content="width=device-width, initial-scale=1">

      <style>
        body {
          font-family: Arial, sans-serif;
          max-width: 850px;
          margin: 50px auto;
          padding: 20px;
          color: #17243a;
          line-height: 1.8;
        }

        h1 {
          font-size: 24px;
          color: #102a56;
        }

        pre {
          white-space: pre-wrap;
          overflow-wrap: anywhere;
          background: #f6f8fb;
          padding: 20px;
          border-radius: 10px;
          font-family: inherit;
        }
      </style>

    </head>

    <body>

      <h1>${safeTitle}</h1>

      <p>${escapeHTML(formatDate(item.createdAt))}</p>

      <pre>${safeContent}</pre>

    </body>
    </html>
  `);

  win.document.close();
}

/* =======================================================
   NAVIGATION
======================================================= */

function navigate(page) {
  document.querySelectorAll(".page").forEach(section => {
    section.classList.toggle(
      "active",
      section.id === `page-${page}`
    );
  });

  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.toggle(
      "active",
      link.dataset.page === page
    );
  });

  const activeLink = document.querySelector(
    `.nav-link[data-page="${page}"]`
  );

  $("currentPageName").textContent = activeLink
    ? activeLink.textContent.trim()
    : "Overview";

  $("sidebar").classList.remove("open");

  if (page === "history") renderHistory();
  if (page === "saved") renderSaved();
  if (page === "overview") renderRecent();

  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
}

function setupNavigation() {
  document.querySelectorAll("[data-page]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      navigate(button.dataset.page);
    });
  });

  document.querySelectorAll("[data-open]").forEach(button => {
    button.addEventListener("click", () => {
      navigate(button.dataset.open);
    });
  });

  $("mobileMenu").addEventListener("click", () => {
    $("sidebar").classList.toggle("open");
  });
}

/* =======================================================
   HISTORY AND SAVED PAGE EVENTS
======================================================= */

function setupHistoryAndSaved() {
  document.addEventListener("click", event => {
    const button = event.target.closest("[data-action]");

    if (!button) return;

    const id = button.dataset.id;
    const isSaved = button.dataset.saved === "true";

    const collection = isSaved
      ? savedItems
      : historyItems;

    const item = collection.find(entry => entry.id === id);

    if (!item) return;

    const action = button.dataset.action;

    if (action === "open") {
      openActivity(item);
    }

    if (action === "copy") {
      copyText(item.content);
    }

    if (action === "delete") {
      savedItems = savedItems.filter(
        entry => entry.id !== id
      );

      saveStorage(STORAGE_KEYS.saved, savedItems);

      renderSaved();

      showToast("Saved item removed.");
    }
  });

  $("clearHistory").addEventListener("click", () => {
    if (!confirm("Clear all TalkBridge history from this browser?")) {
      return;
    }

    historyItems = [];

    saveStorage(STORAGE_KEYS.history, historyItems);

    renderHistory();
    renderRecent();

    showToast("History cleared.");
  });

  $("clearSaved").addEventListener("click", () => {
    if (!confirm("Remove all saved results?")) {
      return;
    }

    savedItems = [];

    saveStorage(STORAGE_KEYS.saved, savedItems);

    renderSaved();

    showToast("Saved items cleared.");
  });

  $("clearLocalData").addEventListener("click", () => {
    if (!confirm(
      "This will clear TalkBridge history, saved items and preferences on this browser. Continue?"
    )) {
      return;
    }

    historyItems = [];
    savedItems = [];

    preferences = { ...DEFAULT_PREFERENCES };

    saveStorage(STORAGE_KEYS.history, []);
    saveStorage(STORAGE_KEYS.saved, []);
    saveStorage(STORAGE_KEYS.preferences, preferences);

    applyPreferences();

    renderHistory();
    renderSaved();
    renderRecent();

    showToast("Local TalkBridge data cleared.");
  });
}

/* =======================================================
   LANGUAGE SELECTORS
======================================================= */

function fillLanguages() {
  const selectors = [
    "sourceLanguage",
    "targetLanguage",
    "imageTargetLanguage",
    "writingLanguage",
    "documentTargetLanguage",
    "conversationSource",
    "conversationTarget",
    "prefSource",
    "prefTarget"
  ];

  selectors.forEach(id => {
    const select = $(id);

    if (!select) return;

    const isSource = [
      "sourceLanguage",
      "conversationSource",
      "prefSource"
    ].includes(id);

    const languages = isSource
      ? LANGUAGES
      : LANGUAGES.filter(
          language => language !== "Auto Detect"
        );

    select.innerHTML = languages
      .map(language => `
        <option value="${escapeHTML(language)}">
          ${escapeHTML(language)}
        </option>
      `)
      .join("");
  });

  document.querySelectorAll(".language-options").forEach(select => {
    if (select.id === "writingLanguage") {
      select.innerHTML = LANGUAGES
        .filter(language => language !== "Auto Detect")
        .map(language => `
          <option value="${escapeHTML(language)}">
            ${escapeHTML(language)}
          </option>
        `)
        .join("");
    }
  });
}

/* =======================================================
   PREFERENCES
======================================================= */

function applyPreferences() {
  $("sourceLanguage").value = preferences.source;
  $("targetLanguage").value = preferences.target;

  $("prefSource").value = preferences.source;
  $("prefTarget").value = preferences.target;

  $("prefAutoplay").checked = Boolean(preferences.autoplay);

  $("prefSpeed").value = preferences.speed;

  $("speedValue").textContent =
    `${Number(preferences.speed).toFixed(1)}x`;

  $("conversationSource").value =
    preferences.source === "Auto Detect"
      ? "English"
      : preferences.source;

  $("conversationTarget").value = preferences.target;

  $("imageTargetLanguage").value = preferences.target;

  $("documentTargetLanguage").value = preferences.target;

  $("writingLanguage").value = "English";
}

function loadPreferencesFromForm() {
  preferences = {
    source: $("prefSource").value,
    target: $("prefTarget").value,
    autoplay: $("prefAutoplay").checked,
    speed: Number($("prefSpeed").value)
  };

  saveStorage(STORAGE_KEYS.preferences, preferences);

  applyPreferences();

  showToast("Preferences saved.");
}

function setupPreferences() {
  $("prefSpeed").addEventListener("input", () => {
    $("speedValue").textContent =
      `${Number($("prefSpeed").value).toFixed(1)}x`;
  });

  $("savePreferences").addEventListener(
    "click",
    loadPreferencesFromForm
  );
}

/* =======================================================
   TRANSLATION INTELLIGENCE
======================================================= */

function setupTranslation() {
  $("translationInput").addEventListener("input", () => {
    $("sourceCount").textContent =
      `${$("translationInput").value.length} / 10000`;
  });

  $("clearTranslation").addEventListener("click", () => {
    $("translationInput").value = "";

    $("sourceCount").textContent = "0 / 10000";

    $("translationOutput").innerHTML =
      '<span class="output-placeholder">Your translation will appear here.</span>';

    $("translationStatus").textContent = "Ready";

    lastTranslation = null;
  });

  $("swapLanguages").addEventListener("click", () => {
    const source = $("sourceLanguage");
    const target = $("targetLanguage");

    if (source.value === "Auto Detect") {
      showToast("Choose a source language before swapping.");
      return;
    }

    const previousSource = source.value;

    source.value = target.value;
    target.value = previousSource;

    const previousText = $("translationInput").value;
    const previousOutput = $("translationOutput").innerText;

    if (
      previousOutput &&
      !previousOutput.includes("Your translation will appear here.")
    ) {
      $("translationInput").value = previousOutput;

      $("translationOutput").textContent = previousText;

      $("sourceCount").textContent =
        `${previousOutput.length} / 10000`;
    }
  });

  $("translateButton").addEventListener("click", translateText);

  $("copyTranslation").addEventListener("click", () => {
    if (!lastTranslation) {
      return showToast("No translation to copy.");
    }

    copyText(lastTranslation.translated_text);
  });

  $("saveTranslation").addEventListener("click", () => {
    if (!lastTranslation) {
      return showToast("No translation to save.");
    }

    saveResult(
      "translation",
      `${lastTranslation.source_language} to ${lastTranslation.target_language}`,
      lastTranslation.translated_text,
      {
        original: lastTranslation.original_text
      }
    );
  });

  $("speakTranslation").addEventListener("click", () => {
    if (!lastTranslation) {
      return showToast("No translation to play.");
    }

    speakText(
      lastTranslation.translated_text,
      lastTranslation.target_language
    );
  });

  // One click handler manages both recording and stopping.
  $("translationMic").addEventListener(
    "click",
    toggleTranslationRecording
  );

  $("cancelTranslationMic").addEventListener(
    "click",
    cancelTranslationRecording
  );
}

async function translateText() {
  const text = $("translationInput").value.trim();

  if (!text) {
    showToast("Enter text to translate.");
    return;
  }

  const button = $("translateButton");

  setButtonLoading(button, true);

  setBusy(
    true,
    "Translating text",
    "Checking the translation database and processing your request."
  );

  try {
    const result = await api("/translation/translate", {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        text,
        source_language: $("sourceLanguage").value,
        target_language: $("targetLanguage").value
      })
    });

    lastTranslation = result;

    $("translationOutput").textContent =
      result.translated_text || "No translation returned.";

    // Display the actual detected language when Auto Detect is used.
    const detectedSource = result.source_language || "Unknown";

    const translationStatus =
      result.status === "verified"
        ? "Verified"
        : "AI generated";

    $("translationStatus").textContent =
      $("sourceLanguage").value === "Auto Detect"
        ? `${detectedSource} detected • ${translationStatus}`
        : translationStatus;

    addHistory(
      "translation",
      `${result.source_language} → ${result.target_language}`,
      result.translated_text,
      {
        original: text,
        provider: result.provider,
        status: result.status
      }
    );

    if (preferences.autoplay && result.translated_text) {
      speakText(
        result.translated_text,
        result.target_language
      );
    }

    showToast("Translation completed.");

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);

    setButtonLoading(
      button,
      false,
      "Translate text →"
    );
  }
}

/* =======================================================
   SPEECH PLAYBACK
======================================================= */

function getSpeechLanguageCode(language) {
  const codes = {
    English: "en-US",
    French: "fr-FR",
    Spanish: "es-ES",
    German: "de-DE",
    Chinese: "zh-CN",
    Arabic: "ar-SA",
    Japanese: "ja-JP",
    Korean: "ko-KR",
    Portuguese: "pt-PT",
    Hindi: "hi-IN",
    Italian: "it-IT",
    Russian: "ru-RU",
    Dutch: "nl-NL",
    Turkish: "tr-TR",
    Swedish: "sv-SE",
    Polish: "pl-PL"
  };

  return codes[language] || "";
}

function speakText(text, language = "English") {
  if (!("speechSynthesis" in window)) {
    showToast("Speech playback is not supported in this browser.");
    return;
  }

  if (!text) return;

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);

  const code = getSpeechLanguageCode(language);

  if (code) {
    utterance.lang = code;
  }

  utterance.rate = Number(preferences.speed) || 1;

  window.speechSynthesis.speak(utterance);
}

/* =======================================================
   TRANSLATION MICROPHONE
======================================================= */

async function toggleTranslationRecording() {
  if (
    translationRecorder &&
    translationRecorder.state === "recording"
  ) {
    stopTranslationRecording();
    return;
  }

  await startTranslationRecording();
}

async function startTranslationRecording() {
  if (
    !navigator.mediaDevices?.getUserMedia ||
    !window.MediaRecorder
  ) {
    showToast(
      "Microphone recording is not supported here. Use HTTPS or localhost."
    );
    return;
  }

  try {
    translationStream =
      await navigator.mediaDevices.getUserMedia({
        audio: true
      });

    translationChunks = [];

    translationRecorder = new MediaRecorder(
      translationStream
    );

    translationRecorder.ondataavailable = event => {
      if (event.data.size) {
        translationChunks.push(event.data);
      }
    };

    translationRecorder.onstop = async () => {
      const mimeType =
        translationRecorder?.mimeType || "audio/webm";

      const blob = new Blob(translationChunks, {
        type: mimeType
      });

      translationStream
        ?.getTracks()
        .forEach(track => track.stop());

      translationStream = null;
      translationRecorder = null;

      $("translationMicStatus").classList.add("hidden");

      $("translationMic").textContent = "🎙 Speak";

      if (blob.size) {
        await transcribeTranslationBlob(blob);
      }
    };

    translationRecorder.start();

    $("translationMicStatus").classList.remove("hidden");

    $("translationMicText").textContent =
      "Recording... Speak now.";

    $("translationMic").textContent = "■ Stop";

  } catch (error) {
    translationStream
      ?.getTracks()
      .forEach(track => track.stop());

    translationStream = null;
    translationRecorder = null;

    showToast(
      "Microphone permission was denied or unavailable."
    );
  }
}

function stopTranslationRecording() {
  if (
    translationRecorder &&
    translationRecorder.state === "recording"
  ) {
    translationRecorder.stop();
  }
}

function cancelTranslationRecording() {
  if (
    translationRecorder &&
    translationRecorder.state !== "inactive"
  ) {
    translationRecorder.onstop = () => {
      translationStream
        ?.getTracks()
        .forEach(track => track.stop());

      translationStream = null;
      translationRecorder = null;
    };

    translationRecorder.stop();
  } else {
    translationStream
      ?.getTracks()
      .forEach(track => track.stop());

    translationStream = null;
    translationRecorder = null;
  }

  $("translationMicStatus").classList.add("hidden");

  $("translationMic").textContent = "🎙 Speak";

  showToast("Recording cancelled.");
}

async function transcribeTranslationBlob(blob) {
  setBusy(
    true,
    "Transcribing your voice",
    "Converting your speech into text."
  );

  try {
    const form = new FormData();

    form.append(
      "file",
      blob,
      "translation-recording.webm"
    );

    const selectedLanguage = $("sourceLanguage").value;

    form.append(
      "language",
      selectedLanguage === "Auto Detect"
        ? ""
        : getSpeechLanguageCode(selectedLanguage)
    );

    const result = await api("/speech/transcribe", {
      method: "POST",
      body: form
    });

    const transcription =
      result.transcribed_text ||
      result.text ||
      "";

    $("translationInput").value = transcription;

    $("sourceCount").textContent =
      `${transcription.length} / 10000`;

    showToast("Speech converted to text.");

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);
  }
}

/* =======================================================
   IMAGE INTELLIGENCE
======================================================= */

function setupImage() {
  $("chooseImage").addEventListener("click", () => {
    $("imageFile").click();
  });

  $("imageFile").addEventListener("change", event => {
    const file = event.target.files[0];

    if (file) {
      selectImage(file);
    }
  });

  setupDropArea(
    $("imageDropArea"),
    selectImage
  );

  $("removeImage").addEventListener("click", () => {
    selectedImageFile = null;

    $("imageFile").value = "";

    $("imagePreviewContainer").classList.add("hidden");
    $("imageResultSection").classList.add("hidden");
    $("imageTranslationResult").classList.add("hidden");

    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
      imagePreviewUrl = null;
    }
  });

  $("analyzeImage").addEventListener("click", () => {
    processImage("analyze");
  });

  $("extractImageText").addEventListener("click", () => {
    processImage("ocr");
  });

  $("translateImageText").addEventListener(
    "click",
    translateImageOCR
  );

  $("saveImageResult").addEventListener("click", () => {
    if (!lastImageResult) return;

    saveResult(
      "image",
      "Image intelligence result",
      lastImageResult
    );
  });
}

function selectImage(file) {
  const allowed = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif"
  ];

  if (!allowed.includes(file.type)) {
    showToast("Choose a JPEG, PNG, WEBP or GIF image.");
    return;
  }

  if (file.size > 10 * 1024 * 1024) {
    showToast("Image must be smaller than 10 MB.");
    return;
  }

  selectedImageFile = file;

  if (imagePreviewUrl) {
    URL.revokeObjectURL(imagePreviewUrl);
  }

  imagePreviewUrl = URL.createObjectURL(file);

  $("imagePreview").src = imagePreviewUrl;

  $("imageFileName").textContent = file.name;

  $("imagePreviewContainer").classList.remove("hidden");

  $("imageResultSection").classList.add("hidden");

  $("imageTranslationResult").classList.add("hidden");

  lastImageResult = null;
}

async function processImage(mode) {
  if (!selectedImageFile) {
    showToast("Select an image first.");
    return;
  }

  const form = new FormData();

  form.append("file", selectedImageFile);

  let endpoint;

  if (mode === "analyze") {
    endpoint = "/image/analyze";

    form.append(
      "question",
      $("imageQuestion").value.trim() ||
      "Describe this image in detail."
    );
  } else {
    endpoint = "/image/extract-text";
  }

  setBusy(
    true,
    mode === "ocr" ? "Extracting text" : "Analyzing image",
    "TalkBridge is processing your image."
  );

  try {
    const result = await api(endpoint, {
      method: "POST",
      body: form
    });

    lastImageResult =
      mode === "ocr"
        ? result.extracted_text
        : result.analysis;

    $("imageResult").textContent =
      lastImageResult || "No result returned.";

    $("imageResultSection").classList.remove("hidden");

    addHistory(
      "image",
      mode === "ocr" ? "Image OCR" : "Image analysis",
      lastImageResult
    );

    showToast(
      mode === "ocr"
        ? "Image text extracted."
        : "Image analyzed."
    );

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);
  }
}

async function translateImageOCR() {
  const extracted = $("imageResult").textContent.trim();

  if (!extracted) {
    showToast("Extract text from the image first.");
    return;
  }

  setBusy(
    true,
    "Translating image text",
    "Detecting the source language and translating the extracted content."
  );

  try {
    const result = await api("/translation/translate", {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        text: extracted,
        source_language: "Auto Detect",
        target_language: $("imageTargetLanguage").value
      })
    });

    const detectedSource =
      result.source_language || "Unknown";

    const output =
      `${result.translated_text}\n\n` +
      `Source language: ${detectedSource}\n` +
      `Translation status: ${result.status}`;

    $("imageTranslationResult").textContent = output;

    $("imageTranslationResult").classList.remove("hidden");

    addHistory(
      "image",
      `Image text translated to ${result.target_language}`,
      result.translated_text,
      {
        original: extracted,
        source_language: detectedSource,
        status: result.status
      }
    );

    showToast("Image text translated.");

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);
  }
}

/* =======================================================
   WRITING INTELLIGENCE
======================================================= */

function setupWriting() {
  $("processWriting").addEventListener(
    "click",
    processWriting
  );

  $("copyWriting").addEventListener("click", () => {
    if (lastWritingResult) {
      copyText(lastWritingResult);
    }
  });

  $("saveWriting").addEventListener("click", () => {
    if (!lastWritingResult) return;

    saveResult(
      "writing",
      "Writing intelligence result",
      lastWritingResult
    );
  });
}

async function processWriting() {
  const text = $("writingInput").value.trim();

  if (!text) {
    showToast("Enter some text first.");
    return;
  }

  const button = $("processWriting");

  setButtonLoading(button, true);

  setBusy(
    true,
    "Improving your writing",
    "Your text is being processed."
  );

  try {
    const result = await api("/writing/process", {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        text,
        task: $("writingTask").value,
        tone: $("writingTone").value || null,
        length: $("writingLength").value,
        language: $("writingLanguage").value
      })
    });

    lastWritingResult = result.processed_text;

    $("writingOutput").textContent = lastWritingResult;

    $("writingResultSection").classList.remove("hidden");

    addHistory(
      "writing",
      `Writing: ${$("writingTask").selectedOptions[0].text}`,
      lastWritingResult,
      {
        original: text,
        task: result.task
      }
    );

    showToast("Writing task completed.");

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);

    setButtonLoading(
      button,
      false,
      "Process writing →"
    );
  }
}

/* =======================================================
   DOCUMENT INTELLIGENCE
======================================================= */

function setupDocuments() {
  $("chooseDocument").addEventListener("click", () => {
    $("documentFile").click();
  });

  $("documentFile").addEventListener("change", event => {
    const file = event.target.files[0];

    if (file) {
      selectDocument(file);
    }
  });

  setupDropArea(
    $("documentDropArea"),
    selectDocument
  );

  $("removeDocument").addEventListener("click", () => {
    selectedDocumentFile = null;

    $("documentFile").value = "";

    $("documentFileInfo").classList.add("hidden");

    $("documentResultSection").classList.add("hidden");

    lastDocumentResult = null;
    documentAudioBlob = null;

    $("documentAudioStatus").textContent = "";
  });

  $("processDocument").addEventListener(
    "click",
    processDocument
  );

  $("exportDocx").addEventListener("click", () => {
    exportDocument("docx");
  });

  $("exportTxt").addEventListener("click", () => {
    exportDocument("txt");
  });

  $("speakDocument").addEventListener("click", () => {
    if (!lastDocumentResult) {
      return showToast("No document result to read.");
    }

    speakText(lastDocumentResult, "English");
  });

  $("downloadDocumentAudio").addEventListener(
    "click",
    downloadDocumentAudio
  );

  $("saveDocumentResult").addEventListener("click", () => {
    if (!lastDocumentResult) return;

    saveResult(
      "document",
      "Document intelligence result",
      lastDocumentResult
    );
  });
}

function selectDocument(file) {
  const allowed = [
    ".pdf",
    ".docx",
    ".txt",
    ".xlsx"
  ];

  const extension =
    "." + file.name.split(".").pop().toLowerCase();

  if (!allowed.includes(extension)) {
    showToast("Choose a PDF, DOCX, TXT or XLSX file.");
    return;
  }

  if (file.size > 20 * 1024 * 1024) {
    showToast("Document must be smaller than 20 MB.");
    return;
  }

  selectedDocumentFile = file;

  $("documentFileName").textContent = file.name;

  $("documentFileSize").textContent =
    `${(file.size / 1024 / 1024).toFixed(2)} MB`;

  $("documentFileInfo").classList.remove("hidden");

  $("documentResultSection").classList.add("hidden");

  lastDocumentResult = null;
}

async function processDocument() {
  if (!selectedDocumentFile) {
    showToast("Select a document first.");
    return;
  }

  const task = $("documentTask").value;

  const form = new FormData();

  form.append("file", selectedDocumentFile);
  form.append("task", task);
  form.append("length", $("documentLength").value);
  form.append(
    "target_language",
    $("documentTargetLanguage").value
  );
  form.append(
    "question",
    $("documentQuestion").value.trim()
  );

  setBusy(
    true,
    "Processing document",
    "Extracting and understanding document content."
  );

  try {
    let result;

    if (task === "extract") {
      const extractForm = new FormData();

      extractForm.append("file", selectedDocumentFile);

      result = await api("/documents/extract", {
        method: "POST",
        body: extractForm
      });

      lastDocumentResult =
        result.extracted_text ||
        result.text ||
        result.content ||
        JSON.stringify(result, null, 2);

    } else {
      result = await api("/documents/process", {
        method: "POST",
        body: form
      });

      lastDocumentResult =
        result.result ||
        result.processed_text ||
        result.output ||
        result.answer ||
        result.translated_text ||
        JSON.stringify(result, null, 2);
    }

    $("documentOutput").textContent = lastDocumentResult;

    $("documentResultSection").classList.remove("hidden");

    documentAudioBlob = null;

    $("documentAudioStatus").textContent = "";

    addHistory(
      "document",
      `${selectedDocumentFile.name} — ${task}`,
      lastDocumentResult,
      {
        task,
        filename: selectedDocumentFile.name
      }
    );

    showToast("Document processing completed.");

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);
  }
}

/* =======================================================
   DOCUMENT EXPORT
======================================================= */

async function exportDocument(format) {
  if (!lastDocumentResult) {
    showToast("Process a document before exporting.");
    return;
  }

  setBusy(
    true,
    "Preparing document",
    `Creating ${format.toUpperCase()} file.`
  );

  try {
    const result = await api(
      `/documents/export/${format}`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({
          text: lastDocumentResult,
          content: lastDocumentResult
        })
      }
    );

    let blob = result;

    if (result && !(result instanceof Blob)) {
      const encoded =
        result.file_base64 ||
        result.content_base64;

      if (encoded) {
        const binary = atob(encoded);

        const bytes = Uint8Array.from(
          binary,
          char => char.charCodeAt(0)
        );

        blob = new Blob([bytes]);
      }
    }

    if (!(blob instanceof Blob)) {
      throw new Error(
        "The export endpoint did not return a downloadable file."
      );
    }

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download = `talkbridge-result.${format}`;

    document.body.appendChild(link);

    link.click();

    link.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);

    showToast(`${format.toUpperCase()} file downloaded.`);

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);
  }
}

/* =======================================================
   DOCUMENT TO AUDIO
======================================================= */

async function generateDocumentAudio() {
  if (!lastDocumentResult) {
    throw new Error(
      "Process a document before generating audio."
    );
  }

  const result = await api("/documents/audio", {
    method: "POST",

    headers: {
      "Content-Type": "application/json"
    },

    body: JSON.stringify({
      text: lastDocumentResult,
      voice: "alloy"
    })
  });

  if (result instanceof Blob) {
    return result;
  }

  if (result.audio_base64) {
    const binary = atob(result.audio_base64);

    const bytes = Uint8Array.from(
      binary,
      char => char.charCodeAt(0)
    );

    return new Blob(
      [bytes],
      { type: "audio/mpeg" }
    );
  }

  if (result.audio_url) {
    const response = await fetch(result.audio_url);

    if (!response.ok) {
      throw new Error("Could not download generated audio.");
    }

    return response.blob();
  }

  throw new Error(
    "The document audio endpoint returned no audio."
  );
}

async function downloadDocumentAudio() {
  setBusy(
    true,
    "Generating document audio",
    "Converting your document result into speech."
  );

  try {
    documentAudioBlob = await generateDocumentAudio();

    const url = URL.createObjectURL(documentAudioBlob);

    const link = document.createElement("a");

    link.href = url;
    link.download = "talkbridge-document-audio.mp3";

    document.body.appendChild(link);

    link.click();

    link.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);

    $("documentAudioStatus").textContent =
      "Audio downloaded.";

    showToast("Document audio downloaded.");

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);
  }
}

/* =======================================================
   SPEECH INTELLIGENCE
======================================================= */

function setupSpeech() {
  $("chooseSpeechFile").addEventListener("click", () => {
    $("speechFile").click();
  });

  $("speechFile").addEventListener("change", event => {
    selectedSpeechFile = event.target.files[0] || null;

    $("speechFileName").textContent =
      selectedSpeechFile
        ? selectedSpeechFile.name
        : "";
  });

  $("startSpeechRecording").addEventListener(
    "click",
    startSpeechRecording
  );

  $("stopSpeechRecording").addEventListener(
    "click",
    stopSpeechRecording
  );

  $("transcribeSpeech").addEventListener(
    "click",
    transcribeSpeech
  );

  $("saveTranscript").addEventListener("click", () => {
    if (!lastTranscript) return;

    saveResult(
      "speech",
      "Speech transcription",
      lastTranscript
    );
  });

  $("startConversation").addEventListener(
    "click",
    startConversationRecording
  );

  $("stopConversation").addEventListener(
    "click",
    stopConversationRecording
  );

  $("saveConversation").addEventListener("click", () => {
    if (!lastConversation) return;

    saveResult(
      "conversation",
      "Translated conversation",
      `${lastConversation.original_text}\n\n${lastConversation.translated_text}`
    );
  });
}

/* =======================================================
   SPEECH RECORDING
======================================================= */

async function startSpeechRecording() {
  if (
    !navigator.mediaDevices?.getUserMedia ||
    !window.MediaRecorder
  ) {
    showToast("Microphone recording requires HTTPS or localhost.");
    return;
  }

  try {
    speechStream =
      await navigator.mediaDevices.getUserMedia({
        audio: true
      });

    speechChunks = [];

    speechRecorder = new MediaRecorder(speechStream);

    speechRecorder.ondataavailable = event => {
      if (event.data.size) {
        speechChunks.push(event.data);
      }
    };

    speechRecorder.onstop = () => {
      const mimeType =
        speechRecorder?.mimeType || "audio/webm";

      const blob = new Blob(speechChunks, {
        type: mimeType
      });

      selectedSpeechFile = new File(
        [blob],
        "speech-recording.webm",
        { type: blob.type }
      );

      $("speechFileName").textContent =
        "Recorded audio ready.";

      speechStream
        ?.getTracks()
        .forEach(track => track.stop());

      speechStream = null;
      speechRecorder = null;

      $("speechRecordingStatus").textContent =
        "Recording completed.";

      $("startSpeechRecording").disabled = false;
      $("stopSpeechRecording").disabled = true;
    };

    speechRecorder.start();

    $("startSpeechRecording").disabled = true;
    $("stopSpeechRecording").disabled = false;

    $("speechRecordingStatus").textContent =
      "Recording... Speak now.";

  } catch (error) {
    speechStream
      ?.getTracks()
      .forEach(track => track.stop());

    speechStream = null;
    speechRecorder = null;

    $("startSpeechRecording").disabled = false;
    $("stopSpeechRecording").disabled = true;

    showToast("Could not access the microphone.");
  }
}

function stopSpeechRecording() {
  if (speechRecorder?.state === "recording") {
    speechRecorder.stop();
  }
}

/* =======================================================
   SPEECH TRANSCRIPTION
======================================================= */

async function transcribeSpeech() {
  if (!selectedSpeechFile) {
    showToast("Upload or record an audio file first.");
    return;
  }

  const form = new FormData();

  form.append("file", selectedSpeechFile);
  form.append("language", "");

  setBusy(
    true,
    "Transcribing speech",
    "Converting audio into text."
  );

  try {
    const result = await api("/speech/transcribe", {
      method: "POST",
      body: form
    });

    lastTranscript =
      result.transcribed_text ||
      result.text ||
      "";

    $("speechTranscript").textContent = lastTranscript;

    $("speechTranscriptSection").classList.remove("hidden");

    addHistory(
      "speech",
      "Speech transcription",
      lastTranscript
    );

    showToast("Speech transcription completed.");

  } catch (error) {
    showToast(error.message);

  } finally {
    setBusy(false);
  }
}

/* =======================================================
   TWO-WAY CONVERSATION
======================================================= */

async function startConversationRecording() {
  if (
    !navigator.mediaDevices?.getUserMedia ||
    !window.MediaRecorder
  ) {
    showToast("Microphone recording requires HTTPS or localhost.");
    return;
  }

  try {
    conversationStream =
      await navigator.mediaDevices.getUserMedia({
        audio: true
      });

    conversationChunks = [];

    conversationRecorder = new MediaRecorder(
      conversationStream
    );

    conversationRecorder.ondataavailable = event => {
      if (event.data.size) {
        conversationChunks.push(event.data);
      }
    };

    conversationRecorder.onstop = async () => {
      const mimeType =
        conversationRecorder?.mimeType || "audio/webm";

      const blob = new Blob(conversationChunks, {
        type: mimeType
      });

      conversationStream
        ?.getTracks()
        .forEach(track => track.stop());

      conversationStream = null;
      conversationRecorder = null;

      $("conversationStatus").textContent =
        "Processing your conversation...";

      $("startConversation").disabled = false;
      $("stopConversation").disabled = true;

      await processConversation(blob);
    };

    conversationRecorder.start();

    $("startConversation").disabled = true;
    $("stopConversation").disabled = false;

    $("conversationStatus").textContent =
      "Recording... Speak now.";

  } catch (error) {
    conversationStream
      ?.getTracks()
      .forEach(track => track.stop());

    conversationStream = null;
    conversationRecorder = null;

    $("startConversation").disabled = false;
    $("stopConversation").disabled = true;

    showToast("Could not access the microphone.");
  }
}

function stopConversationRecording() {
  if (conversationRecorder?.state === "recording") {
    conversationRecorder.stop();
  }
}

async function processConversation(blob) {
  const form = new FormData();

  form.append("file", blob, "conversation.webm");

  form.append(
    "source_language",
    $("conversationSource").value
  );

  form.append(
    "target_language",
    $("conversationTarget").value
  );

  form.append(
    "voice",
    $("conversationVoice").value
  );

  setBusy(
    true,
    "Translating conversation",
    "Transcribing and translating your message."
  );

  try {
    const result = await api(
      "/speech/conversation-turn",
      {
        method: "POST",
        body: form
      }
    );

    const original =
      result.original_text ||
      result.transcribed_text ||
      "";

    const translated =
      result.translated_text || "";

    lastConversation = {
      original_text: original,
      translated_text: translated
    };

    $("conversationOriginal").textContent = original;

    $("conversationTranslated").textContent = translated;

    $("conversationResultSection").classList.remove("hidden");

    // Remove previous conversation audio URL.
    if (conversationAudioUrl) {
      URL.revokeObjectURL(conversationAudioUrl);
      conversationAudioUrl = null;
    }

    const audioBase64 = result.audio_base64;

    if (audioBase64) {
      const binary = atob(audioBase64);

      const bytes = Uint8Array.from(
        binary,
        char => char.charCodeAt(0)
      );

      const audioBlob = new Blob(
        [bytes],
        { type: "audio/mpeg" }
      );

      conversationAudioUrl =
        URL.createObjectURL(audioBlob);

      $("conversationAudio").src =
        conversationAudioUrl;

      $("conversationAudio").classList.remove("hidden");

      if (preferences.autoplay) {
        $("conversationAudio").play().catch(() => {});
      }

    } else if (result.audio_url) {
      $("conversationAudio").src = result.audio_url;

      $("conversationAudio").classList.remove("hidden");

      if (preferences.autoplay) {
        $("conversationAudio").play().catch(() => {});
      }

    } else {
      $("conversationAudio").removeAttribute("src");

      $("conversationAudio").classList.add("hidden");
    }

    addHistory(
      "conversation",
      `${$("conversationSource").value} → ${$("conversationTarget").value}`,
      `${original}\n\n${translated}`
    );

    $("conversationStatus").textContent =
      "Conversation completed.";

    showToast("Conversation translated.");

  } catch (error) {
    $("conversationStatus").textContent =
      "Conversation failed.";

    showToast(error.message);

  } finally {
    setBusy(false);
  }
}

/* =======================================================
   FILE DROP AREAS
======================================================= */

function setupDropArea(element, callback) {
  if (!element) return;

  ["dragenter", "dragover"].forEach(name => {
    element.addEventListener(name, event => {
      event.preventDefault();

      element.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach(name => {
    element.addEventListener(name, event => {
      event.preventDefault();

      element.classList.remove("drag-over");
    });
  });

  element.addEventListener("drop", event => {
    const file = event.dataTransfer?.files?.[0];

    if (file) {
      callback(file);
    }
  });
}

/* =======================================================
   INITIALIZATION
======================================================= */

function initializeTalkBridge() {
  fillLanguages();

  applyPreferences();

  setupNavigation();

  setupHistoryAndSaved();

  setupTranslation();

  setupImage();

  setupWriting();

  setupDocuments();

  setupSpeech();

  setupPreferences();

  renderHistory();

  renderSaved();

  renderRecent();

  console.log("TalkBridge 2.0 frontend initialized.");
}

document.addEventListener(
  "DOMContentLoaded",
  initializeTalkBridge
);