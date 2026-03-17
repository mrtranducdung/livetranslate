/**
 * Mistral Translation — calls Mistral AI chat API to translate text
 */

const LANG_NAMES = {
    'en': 'English', 'vi': 'Vietnamese', 'ja': 'Japanese',
    'ko': 'Korean', 'zh': 'Chinese', 'fr': 'French',
    'de': 'German', 'es': 'Spanish', 'th': 'Thai', 'id': 'Indonesian',
};

class MistralTranslate {
    constructor() {
        this.apiKey = null;
        this.model = 'mistral-small-latest';
    }

    configure({ apiKey }) {
        this.apiKey = apiKey;
    }

    /**
     * Translate text to target language.
     * @param {string} text
     * @param {string} sourceLang - language code or 'auto'
     * @param {string} targetLang - language code
     * @returns {Promise<string|null>}
     */
    async translate(text, sourceLang, targetLang) {
        if (!this.apiKey || !text?.trim()) return null;

        const target = LANG_NAMES[targetLang] || targetLang;
        const sourceHint = (sourceLang && sourceLang !== 'auto')
            ? ` from ${LANG_NAMES[sourceLang] || sourceLang}`
            : '';

        const prompt = `Translate the following text${sourceHint} to ${target}. Output only the translation, nothing else.\n\n${text}`;

        try {
            const response = await fetch('https://api.mistral.ai/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.apiKey}`,
                },
                body: JSON.stringify({
                    model: this.model,
                    messages: [{ role: 'user', content: prompt }],
                    temperature: 0.1,
                }),
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                console.error('[Mistral] Error:', response.status, err);
                return null;
            }

            const data = await response.json();
            return data.choices?.[0]?.message?.content?.trim() || null;
        } catch (e) {
            console.error('[Mistral] Request failed:', e);
            return null;
        }
    }
}

export const mistralTranslate = new MistralTranslate();
