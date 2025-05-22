// Gerenciador de Cookies
const CookieManager = {
    clientId: null,

    // Inicializa o gerenciador
    init: function() {
        // Tenta recuperar o client_id do localStorage
        this.clientId = localStorage.getItem('cookieClientId');
        
        // Se não existir, cria um novo
        if (!this.clientId) {
            this.clientId = crypto.randomUUID();
            localStorage.setItem('cookieClientId', this.clientId);
        }
        
        // Carrega as preferências do servidor
        this.loadServerPreferences();
    },

    // Carrega preferências do servidor
    loadServerPreferences: async function() {
        try {
            const response = await fetch(`/api/cookies/preferences/${this.clientId}/`);
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success') {
                    this.applyCookiePreferences(data.preferences);
                    return data.preferences;
                }
            }
        } catch (error) {
            console.error('Erro ao carregar preferências:', error);
        }
        
        // Se houver erro, usa as preferências locais
        return this.loadLocalPreferences();
    },

    // Salva as preferências no servidor
    saveServerPreferences: async function(preferences) {
        try {
            const response = await fetch('/api/cookies/preferences/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    client_id: this.clientId,
                    ...preferences
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success') {
                    console.log('Preferências salvas com sucesso');
                    return true;
                }
            }
        } catch (error) {
            console.error('Erro ao salvar preferências:', error);
        }
        return false;
    },

    // Verifica se o usuário já aceitou os cookies
    checkCookieConsent: function() {
        return localStorage.getItem('cookieConsent') !== null;
    },

    // Salva as preferências de cookies
    async saveCookiePreferences(preferences) {
        // Salva localmente
        localStorage.setItem('cookieConsent', JSON.stringify(preferences));
        this.hideCookieConsent();
        
        // Tenta salvar no servidor
        await this.saveServerPreferences(preferences);
        
        // Aplica as preferências
        this.applyCookiePreferences(preferences);
    },

    // Carrega as preferências de cookies
    async loadCookiePreferences() {
        // Tenta carregar do servidor primeiro
        const serverPreferences = await this.loadServerPreferences();
        if (serverPreferences) {
            return serverPreferences;
        }
        
        // Se não conseguir, usa as preferências locais
        const savedPreferences = localStorage.getItem('cookieConsent');
        if (savedPreferences) {
            return JSON.parse(savedPreferences);
        }
        
        // Preferências padrão (todos os cookies ativos)
        return {
            essential: true,
            performance: true,
            marketing: true,
            timestamp: new Date().toISOString()
        };
    },

    // Mostra o modal de consentimento
    showCookieConsent: function() {
        if (!this.checkCookieConsent()) {
            document.getElementById('cookieConsent').classList.add('show');
            // Marca os checkboxes por padrão
            document.getElementById('performanceCookies').checked = true;
            document.getElementById('marketingCookies').checked = true;
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
    },

    // Aplica as preferências de cookies
    applyCookiePreferences: function(preferences) {
        // Cookies essenciais sempre ativos
        this.setEssentialCookies(true);

        // Aplica cookies de desempenho
        if (preferences.performance) {
            this.setPerformanceCookies(true);
        } else {
            this.setPerformanceCookies(false);
        }

        // Aplica cookies de marketing
        if (preferences.marketing) {
            this.setMarketingCookies(true);
        } else {
            this.setMarketingCookies(false);
        }
    },

    // Funções específicas para cada tipo de cookie
    setEssentialCookies: function(enabled) {
        // Implementar lógica para cookies essenciais
        // Por exemplo: csrf token, sessão, etc.
        console.log('Cookies essenciais:', enabled ? 'ativados' : 'desativados');
    },

    setPerformanceCookies: function(enabled) {
        if (enabled) {
            // Implementar lógica para ativar cookies de desempenho
            // Por exemplo: Google Analytics
            console.log('Cookies de desempenho ativados');
            // Exemplo: inicializar Google Analytics
            // if (typeof gtag !== 'undefined') {
            //     gtag('consent', 'update', {
            //         'analytics_storage': 'granted'
            //     });
            // }
        } else {
            // Implementar lógica para desativar cookies de desempenho
            console.log('Cookies de desempenho desativados');
            // Exemplo: desativar Google Analytics
            // if (typeof gtag !== 'undefined') {
            //     gtag('consent', 'update', {
            //         'analytics_storage': 'denied'
            //     });
            // }
        }
    },

    setMarketingCookies: function(enabled) {
        if (enabled) {
            // Implementar lógica para ativar cookies de marketing
            // Por exemplo: Facebook Pixel, Google Ads
            console.log('Cookies de marketing ativados');
            // Exemplo: inicializar Facebook Pixel
            // if (typeof fbq !== 'undefined') {
            //     fbq('consent', 'grant');
            // }
        } else {
            // Implementar lógica para desativar cookies de marketing
            console.log('Cookies de marketing desativados');
            // Exemplo: desativar Facebook Pixel
            // if (typeof fbq !== 'undefined') {
            //     fbq('consent', 'revoke');
            // }
        }
    }
};

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa o gerenciador de cookies
    CookieManager.init();
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
    cookieSettingsModal.addEventListener('show.bs.modal', async function() {
        const preferences = await CookieManager.loadCookiePreferences();
        if (preferences) {
            document.getElementById('performanceCookies').checked = preferences.performance;
            document.getElementById('marketingCookies').checked = preferences.marketing;
        }
    });
}); 