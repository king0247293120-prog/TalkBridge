const API_URL = "https://talkbridge-api.onrender.com/";


// ============================================================
// LANGUAGES
// ============================================================

const languages = [
    {
        name: "English",
        code: "en",
        flag: "🇬🇧"
    },
    {
        name: "Chinese",
        code: "zh",
        flag: "🇨🇳"
    },
    {
        name: "Spanish",
        code: "es",
        flag: "🇪🇸"
    },
    {
        name: "French",
        code: "fr",
        flag: "🇫🇷"
    },
    {
        name: "German",
        code: "de",
        flag: "🇩🇪"
    },
    {
        name: "Portuguese",
        code: "pt",
        flag: "🇵🇹"
    },
    {
        name: "Arabic",
        code: "ar",
        flag: "🇸🇦"
    },
    {
        name: "Japanese",
        code: "ja",
        flag: "🇯🇵"
    },
    {
        name: "Korean",
        code: "ko",
        flag: "🇰🇷"
    },
    {
        name: "Italian",
        code: "it",
        flag: "🇮🇹"
    },
    {
        name: "Russian",
        code: "ru",
        flag: "🇷🇺"
    },
    {
        name: "Hindi",
        code: "hi",
        flag: "🇮🇳"
    },
    {
        name: "Turkish",
        code: "tr",
        flag: "🇹🇷"
    },
    {
        name: "Dutch",
        code: "nl",
        flag: "🇳🇱"
    },
    {
        name: "Swedish",
        code: "sv",
        flag: "🇸🇪"
    },
    {
        name: "Polish",
        code: "pl",
        flag: "🇵🇱"
    },
    {
        name: "Twi",
        code: "tw",
        flag: "🇬🇭"
    },
    {
        name: "Ewe",
        code: "ee",
        flag: "🇬🇭"
    },
    {
        name: "Ga",
        code: "gaa",
        flag: "🇬🇭"
    },
    {
        name: "Dagbani",
        code: "dag",
        flag: "🇬🇭"
    },
    {
        name: "Fante",
        code: "fat",
        flag: "🇬🇭"
    }
];


// ============================================================
// APPLICATION STATE
// ============================================================

let fromLanguage = languages[0];
let toLanguage = languages[1];

let languageSelectionTarget = null;

let mediaRecorder = null;
let microphoneStream = null;
let recordedChunks = [];

let conversationRecorder = null;
let conversationStream = null;

let conversationRunning = false;
let conversationProcessing = false;

let lastAudioUrl = null;

let autoPlay = true;
let speechSpeed = 1;


// ============================================================
// ELEMENTS
// ============================================================

const textInput = document.getElementById("textInput");
const characterCount = document.getElementById("characterCount");

const translateButton = document.getElementById("translateButton");

const translationResult =
    document.getElementById("translationResult");

const speakerButton =
    document.getElementById("speakerButton");

const micButton =
    document.getElementById("micButton");

const clearButton =
    document.getElementById("clearButton");

const swapButton =
    document.getElementById("swapButton");

const fromLanguageButton =
    document.getElementById("fromLanguageButton");

const toLanguageButton =
    document.getElementById("toLanguageButton");

const languageModal =
    document.getElementById("languageModal");

const languageModalTitle =
    document.getElementById("languageModalTitle");

const languageSearch =
    document.getElementById("languageSearch");

const languageList =
    document.getElementById("languageList");

const closeLanguageModal =
    document.getElementById("closeLanguageModal");

const conversationButton =
    document.getElementById("conversationButton");

const conversationModal =
    document.getElementById("conversationModal");

const closeConversationModal =
    document.getElementById("closeConversationModal");

const conversationMic =
    document.getElementById("conversationMic");

const conversationMicText =
    document.getElementById("conversationMicText");

const conversationStatus =
    document.getElementById("conversationStatus");

const conversationMessages =
    document.getElementById("conversationMessages");

const settingsButton =
    document.getElementById("settingsButton");

const settingsModal =
    document.getElementById("settingsModal");

const closeSettingsModal =
    document.getElementById("closeSettingsModal");

const autoPlayCheckbox =
    document.getElementById("autoPlay");

const speechSpeedSelect =
    document.getElementById("speechSpeed");

const loading =
    document.getElementById("loading");

const loadingText =
    document.getElementById("loadingText");


// ============================================================
// LANGUAGE UI
// ============================================================

function updateLanguageUI() {

    document.getElementById("fromFlag").textContent =
        fromLanguage.flag;

    document.getElementById("fromLanguage").textContent =
        fromLanguage.name;

    document.getElementById("toFlag").textContent =
        toLanguage.flag;

    document.getElementById("toLanguage").textContent =
        toLanguage.name;

    document.getElementById("inputLanguageTitle").textContent =
        fromLanguage.name;

    document.getElementById("outputLanguageTitle").textContent =
        toLanguage.name;

    document.getElementById("conversationFromFlag").textContent =
        fromLanguage.flag;

    document.getElementById("conversationFromLanguage").textContent =
        fromLanguage.name;

    document.getElementById("conversationToFlag").textContent =
        toLanguage.flag;

    document.getElementById("conversationToLanguage").textContent =
        toLanguage.name;
}


updateLanguageUI();


// ============================================================
// LANGUAGE MODAL
// ============================================================

function openLanguageModal(target) {

    languageSelectionTarget = target;

    languageModalTitle.textContent =
        target === "from"
            ? "Translate from"
            : "Translate to";

    languageSearch.value = "";

    renderLanguages("");

    languageModal.classList.remove("hidden");

    setTimeout(() => {
        languageSearch.focus();
    }, 100);
}


function closeLanguageSelector() {

    languageModal.classList.add("hidden");

    languageSelectionTarget = null;
}


function renderLanguages(searchTerm) {

    const search = searchTerm.toLowerCase().trim();

    languageList.innerHTML = "";

    const filtered = languages.filter(language =>
        language.name.toLowerCase().includes(search)
    );

    filtered.forEach(language => {

        const button =
            document.createElement("button");

        button.className = "language-option";

        button.innerHTML = `
            <span>${language.flag}</span>
            <span>${language.name}</span>
        `;

        button.addEventListener("click", () => {

            if (languageSelectionTarget === "from") {

                if (language.code === toLanguage.code) {
                    alert("Choose two different languages.");
                    return;
                }

                fromLanguage = language;

            } else {

                if (language.code === fromLanguage.code) {
                    alert("Choose two different languages.");
                    return;
                }

                toLanguage = language;
            }

            updateLanguageUI();

            closeLanguageSelector();
        });

        languageList.appendChild(button);
    });
}


fromLanguageButton.addEventListener(
    "click",
    () => openLanguageModal("from")
);

toLanguageButton.addEventListener(
    "click",
    () => openLanguageModal("to")
);

closeLanguageModal.addEventListener(
    "click",
    closeLanguageSelector
);

languageSearch.addEventListener(
    "input",
    e => renderLanguages(e.target.value)
);


// ============================================================
// SWAP
// ============================================================

swapButton.addEventListener("click", () => {

    const temporary = fromLanguage;

    fromLanguage = toLanguage;
    toLanguage = temporary;

    updateLanguageUI();
});


// ============================================================
// CHARACTER COUNT
// ============================================================

textInput.addEventListener("input", () => {

    characterCount.textContent =
        `${textInput.value.length} / 1000`;
});


// ============================================================
// CLEAR
// ============================================================

clearButton.addEventListener("click", () => {

    textInput.value = "";

    characterCount.textContent =
        "0 / 1000";

    translationResult.textContent =
        "Your translation will appear here.";
});


// ============================================================
// LOADING
// ============================================================

function showLoading(message) {

    loadingText.textContent = message;

    loading.classList.remove("hidden");
}


function hideLoading() {

    loading.classList.add("hidden");
}


// ============================================================
// NORMAL TRANSLATION
// ============================================================

translateButton.addEventListener(
    "click",
    translateText
);


async function translateText() {

    const text = textInput.value.trim();

    if (!text) {

        alert("Enter something to translate.");

        return;
    }

    translateButton.disabled = true;

    showLoading("Translating...");

    try {

        const response =
            await fetch(`${API_URL}/translate`, {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    text: text,

                    source_language:
                        fromLanguage.name,

                    target_language:
                        toLanguage.name
                })
            });


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail || "Translation failed."
            );
        }


        translationResult.textContent =
            data.translation;


        if (autoPlay) {

            await playTranslationAudio(
                data.translation,
                toLanguage.code
            );
        }

    } catch (error) {

        console.error(error);

        translationResult.textContent =
            "Translation failed. Check that the backend is running and your API key is configured.";

        alert(error.message);

    } finally {

        translateButton.disabled = false;

        hideLoading();
    }
}


// ============================================================
// MICROPHONE - NORMAL MODE
// ============================================================

micButton.addEventListener(
    "click",
    toggleNormalMicrophone
);


async function toggleNormalMicrophone() {

    if (
        mediaRecorder &&
        mediaRecorder.state === "recording"
    ) {

        mediaRecorder.stop();

        return;
    }


    try {

        microphoneStream =
            await navigator.mediaDevices.getUserMedia({
                audio: true
            });


        recordedChunks = [];


        mediaRecorder =
            new MediaRecorder(
                microphoneStream
            );


        mediaRecorder.ondataavailable =
            event => {

                if (event.data.size > 0) {

                    recordedChunks.push(
                        event.data
                    );
                }
            };


        mediaRecorder.onstop =
            async () => {

                stopMicrophoneStream();

                micButton.classList.remove(
                    "recording"
                );

                micButton.textContent = "🎤";


                const audioBlob =
                    new Blob(
                        recordedChunks,
                        {
                            type: "audio/webm"
                        }
                    );


                await transcribeNormalAudio(
                    audioBlob
                );
            };


        mediaRecorder.start();

        micButton.classList.add(
            "recording"
        );

        micButton.textContent = "⏹";

    } catch (error) {

        console.error(error);

        alert(
            "Microphone permission was denied or unavailable."
        );
    }
}


function stopMicrophoneStream() {

    if (!microphoneStream) {
        return;
    }

    microphoneStream
        .getTracks()
        .forEach(track => track.stop());

    microphoneStream = null;
}


// ============================================================
// TRANSCRIBE NORMAL AUDIO
// ============================================================

async function transcribeNormalAudio(audioBlob) {

    showLoading("Understanding your speech...");

    try {

        const formData =
            new FormData();

        formData.append(
            "file",
            audioBlob,
            "speech.webm"
        );


        formData.append(
            "language",
            fromLanguage.code
        );


        const response =
            await fetch(
                `${API_URL}/speech/transcribe`,
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Speech recognition failed."
            );
        }


        textInput.value =
            data.text;


        characterCount.textContent =
            `${data.text.length} / 1000`;


        hideLoading();

        await translateText();

    } catch (error) {

        console.error(error);

        hideLoading();

        alert(error.message);
    }
}


// ============================================================
// TTS
// ============================================================

async function playTranslationAudio(
    text,
    languageCode
) {

    try {

        const response =
            await fetch(
                `${API_URL}/speech`,
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        text: text,

                        language:
                            languageCode,

                        speed:
                            speechSpeed
                    })
                }
            );


        if (!response.ok) {

            const errorData =
                await response.json();

            throw new Error(
                errorData.detail ||
                "Audio generation failed."
            );
        }


        const blob =
            await response.blob();


        if (lastAudioUrl) {

            URL.revokeObjectURL(
                lastAudioUrl
            );
        }


        lastAudioUrl =
            URL.createObjectURL(blob);


        const audio =
            new Audio(lastAudioUrl);


        await audio.play();

    } catch (error) {

        console.error(error);

        console.warn(
            "Could not play translated audio:",
            error.message
        );
    }
}


speakerButton.addEventListener(
    "click",
    async () => {

        const text =
            translationResult.textContent.trim();

        if (
            !text ||
            text === "Your translation will appear here."
        ) {

            return;
        }

        await playTranslationAudio(
            text,
            toLanguage.code
        );
    }
);


// ============================================================
// CONVERSATION MODE
// ============================================================

conversationButton.addEventListener(
    "click",
    openConversation
);


function openConversation() {

    updateLanguageUI();

    conversationModal.classList.remove(
        "hidden"
    );
}


closeConversationModal.addEventListener(
    "click",
    async () => {

        if (conversationRunning) {

            await stopConversation();
        }

        conversationModal.classList.add(
            "hidden"
        );
    }
);


// ============================================================
// START / STOP CONTINUOUS CONVERSATION
// ============================================================

conversationMic.addEventListener(
    "click",
    async () => {

        if (conversationRunning) {

            await stopConversation();

        } else {

            await startConversation();
        }
    }
);


async function startConversation() {

    if (conversationRunning) {
        return;
    }


    try {

        conversationStream =
            await navigator.mediaDevices.getUserMedia({
                audio: true
            });


        conversationRunning = true;


        conversationMic.classList.add(
            "listening"
        );

        conversationMicText.textContent =
            "Stop Listening";


        conversationStatus.textContent =
            "Listening...";

        conversationStatus.classList.add(
            "listening"
        );


        conversationMessages.innerHTML = "";


        startConversationRecording();

    } catch (error) {

        console.error(error);

        alert(
            "Microphone permission is required for Conversation Mode."
        );
    }
}


async function stopConversation() {

    conversationRunning = false;


    if (
        conversationRecorder &&
        conversationRecorder.state === "recording"
    ) {

        conversationRecorder.stop();
    }


    if (conversationStream) {

        conversationStream
            .getTracks()
            .forEach(
                track => track.stop()
            );

        conversationStream = null;
    }


    conversationMic.classList.remove(
        "listening"
    );

    conversationMicText.textContent =
        "Start Listening";


    conversationStatus.textContent =
        "Stopped";

    conversationStatus.classList.remove(
        "listening"
    );
}


// ============================================================
// CONTINUOUS RECORDING LOOP
// ============================================================

function startConversationRecording() {

    if (!conversationRunning) {
        return;
    }


    recordedChunks = [];


    conversationRecorder =
        new MediaRecorder(
            conversationStream
        );


    conversationRecorder.ondataavailable =
        event => {

            if (event.data.size > 0) {

                recordedChunks.push(
                    event.data
                );
            }
        };


    conversationRecorder.onstop =
        async () => {

            if (!conversationRunning) {
                return;
            }


            const audioBlob =
                new Blob(
                    recordedChunks,
                    {
                        type: "audio/webm"
                    }
                );


            if (audioBlob.size > 1000) {

                await processConversationAudio(
                    audioBlob
                );

            } else {

                if (conversationRunning) {

                    startConversationRecording();
                }
            }
        };


    // Record a short chunk.
    // The loop starts the next chunk automatically.
    conversationRecorder.start();


    setTimeout(() => {

        if (
            conversationRunning &&
            conversationRecorder &&
            conversationRecorder.state === "recording"
        ) {

            conversationRecorder.stop();
        }

    }, 5000);
}


// ============================================================
// PROCESS CONVERSATION AUDIO
// ============================================================

async function processConversationAudio(
    audioBlob
) {

    if (conversationProcessing) {

        return;
    }


    conversationProcessing = true;


    conversationStatus.textContent =
        "Understanding speech...";


    try {

        const formData =
            new FormData();


        formData.append(
            "file",
            audioBlob,
            "conversation.webm"
        );


        // We deliberately do NOT tell the
        // transcription endpoint which language
        // was spoken.
        //
        // The backend detects the language.

        const transcriptionResponse =
            await fetch(
                `${API_URL}/conversation/transcribe`,
                {
                    method: "POST",
                    body: formData
                }
            );


        const transcriptionData =
            await transcriptionResponse.json();


        if (!transcriptionResponse.ok) {

            throw new Error(
                transcriptionData.detail ||
                "Conversation transcription failed."
            );
        }


        const spokenText =
            transcriptionData.text.trim();


        const detectedLanguage =
            transcriptionData.language;


        if (!spokenText) {

            conversationProcessing = false;

            if (conversationRunning) {

                conversationStatus.textContent =
                    "Listening...";

                startConversationRecording();
            }

            return;
        }


        // ====================================================
        // IMPORTANT:
        // Only accept one of the two selected languages.
        // ====================================================

        const fromDetected =
            languagesMatch(
                detectedLanguage,
                fromLanguage
            );

        const toDetected =
            languagesMatch(
                detectedLanguage,
                toLanguage
            );


        let targetLanguage;


        if (fromDetected) {

            targetLanguage =
                toLanguage;

        } else if (toDetected) {

            targetLanguage =
                fromLanguage;

        } else {

            // The AI heard another language.
            // We don't translate it.

            addConversationMessage({

                detected:
                    detectedLanguage ||
                    "Unknown",

                original:
                    spokenText,

                translation:
                    "This is not one of the two selected languages."
            });


            conversationProcessing = false;

            if (conversationRunning) {

                conversationStatus.textContent =
                    "Listening...";

                startConversationRecording();
            }

            return;
        }


        conversationStatus.textContent =
            `Detected ${getLanguageName(detectedLanguage)} → ${targetLanguage.name}`;


        // ====================================================
        // TRANSLATE
        // ====================================================

        const translationResponse =
            await fetch(
                `${API_URL}/translate`,
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        text:
                            spokenText,

                        source_language:
                            getLanguageName(
                                detectedLanguage
                            ),

                        target_language:
                            targetLanguage.name
                    })
                }
            );


        const translationData =
            await translationResponse.json();


        if (!translationResponse.ok) {

            throw new Error(
                translationData.detail ||
                "Conversation translation failed."
            );
        }


        const translatedText =
            translationData.translation;


        addConversationMessage({

            detected:
                getLanguageName(
                    detectedLanguage
                ),

            original:
                spokenText,

            translation:
                translatedText
        });


        // ====================================================
        // SPEAK TRANSLATION
        // ====================================================

        if (autoPlay) {

            await playTranslationAudio(
                translatedText,
                targetLanguage.code
            );
        }


    } catch (error) {

        console.error(error);

        addConversationMessage({

            detected: "Error",

            original: "Could not understand audio.",

            translation: error.message
        });

    } finally {

        conversationProcessing = false;


        if (conversationRunning) {

            conversationStatus.textContent =
                "Listening...";

            // Start receiving another chunk.
            startConversationRecording();
        }
    }
}


// ============================================================
// LANGUAGE MATCHING
// ============================================================

function languagesMatch(
    detectedCode,
    language
) {

    if (!detectedCode) {
        return false;
    }


    const detected =
        detectedCode.toLowerCase();


    const selected =
        language.code.toLowerCase();


    if (detected === selected) {
        return true;
    }


    // Some APIs may return language
    // variants such as en-US.

    if (
        detected.startsWith(
            selected + "-"
        )
    ) {

        return true;
    }


    return false;
}


function getLanguageName(code) {

    if (!code) {
        return "Unknown";
    }


    const normalized =
        code.toLowerCase();


    const language =
        languages.find(
            item =>
                item.code.toLowerCase() ===
                normalized
        );


    if (language) {
        return language.name;
    }


    return code;
}


// ============================================================
// CONVERSATION MESSAGE UI
// ============================================================

function addConversationMessage({
    detected,
    original,
    translation
}) {

    const empty =
        conversationMessages.querySelector(
            ".empty-conversation"
        );


    if (empty) {
        empty.remove();
    }


    const message =
        document.createElement("div");


    message.className =
        "conversation-message";


    message.innerHTML = `

        <div class="detected-language">
            Detected: ${escapeHtml(detected)}
        </div>

        <div class="original-text">
            ${escapeHtml(original)}
        </div>

        <div class="translated-text">
            → ${escapeHtml(translation)}
        </div>

    `;


    conversationMessages.appendChild(
        message
    );


    conversationMessages.scrollTop =
        conversationMessages.scrollHeight;
}


function escapeHtml(value) {

    const div =
        document.createElement("div");

    div.textContent = value;

    return div.innerHTML;
}


// ============================================================
// SETTINGS
// ============================================================

settingsButton.addEventListener(
    "click",
    () => {

        settingsModal.classList.remove(
            "hidden"
        );
    }
);


closeSettingsModal.addEventListener(
    "click",
    () => {

        settingsModal.classList.add(
            "hidden"
        );
    }
);


autoPlayCheckbox.addEventListener(
    "change",
    () => {

        autoPlay =
            autoPlayCheckbox.checked;
    }
);


speechSpeedSelect.addEventListener(
    "change",
    () => {

        speechSpeed =
            Number(
                speechSpeedSelect.value
            );
    }
);


// ============================================================
// CLOSE MODALS WHEN CLICKING OUTSIDE
// ============================================================

window.addEventListener(
    "click",
    event => {

        if (
            event.target ===
            languageModal
        ) {

            closeLanguageSelector();
        }


        if (
            event.target ===
            settingsModal
        ) {

            settingsModal.classList.add(
                "hidden"
            );
        }
    }
);