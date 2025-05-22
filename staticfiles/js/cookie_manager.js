// Gerenciador de Cookies
const CookieManager = {
    // Verifica se o usuário já aceitou os cookies
    checkCookieConsent: function() {
        return localStorage.getItem('cookieConsent') !== null;
    },

    // Salva as preferências de cookies
    saveCookiePreferences: function(preferences) {
        localStorage.setItem('cookieConsent', JSON.stringify(preferences));
        this.hideCookieConsent();
    },

    // Carrega as preferências de cookies
    loadCookiePreferences: function() {
        const savedPreferences = localStorage.getItem('cookieConsent');
        return savedPreferences ? JSON.parse(savedPreferences) : null;
    },

    // Mostra o modal de consentimento
    showCookieConsent: function() {
        if (!this.checkCookieConsent()) {
            document.getElementById('cookieConsent').classList.add('show');
        }
    },

    // Esconde o modal de consentimento
    hideCookieConsent: function() {
        document.getElementById('cookieConsent').classList.remove('show');
    },

    // Aceita todos os cookies
    acceptAllCookies: function() {
        const preferences = {
            essential: true,
            performance: true,
            marketing: true,
            timestamp: new Date().toISOString()
        };
        this.saveCookiePreferences(preferences);
    },

    // Salva as configurações personalizadas
    saveCustomPreferences: function() {
        const preferences = {
            essential: true, // Sempre true
            performance: document.getElementById('performanceCookies').checked,
            marketing: document.getElementById('marketingCookies').checked,
            timestamp: new Date().toISOString()
        };
        this.saveCookiePreferences(preferences);
    }
};

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa o gerenciador de cookies
    CookieManager.showCookieConsent();

    // Event Listeners
    document.getElementById('acceptCookies').addEventListener('click', function() {
        CookieManager.acceptAllCookies();
    });

    document.getElementById('saveCookieSettings').addEventListener('click', function() {
        CookieManager.saveCustomPreferences();
        const cookieSettingsModal = bootstrap.Modal.getInstance(document.getElementById('cookieSettingsModal'));
        cookieSettingsModal.hide();
    });

    // Carrega as preferências salvas no modal de configurações
    const cookieSettingsModal = document.getElementById('cookieSettingsModal');
    cookieSettingsModal.addEventListener('show.bs.modal', function() {
        const preferences = CookieManager.loadCookiePreferences();
        if (preferences) {
            document.getElementById('performanceCookies').checked = preferences.performance;
            document.getElementById('marketingCookies').checked = preferences.marketing;
        }
    });
}); 