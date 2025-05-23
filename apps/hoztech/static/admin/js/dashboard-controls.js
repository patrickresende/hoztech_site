// Configurações globais do Chart.js para desabilitar animações
Chart.defaults.animation = false;
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;

// Função para prevenir atualizações automáticas
function preventAutoUpdates() {
    // Remove qualquer intervalo de atualização que possa existir
    const intervals = window.setInterval(function(){}, 9999);
    for (let i = 0; i < intervals; i++) {
        window.clearInterval(i);
    }
    
    // Remove qualquer timeout que possa existir
    const timeouts = window.setTimeout(function(){}, 9999);
    for (let i = 0; i < timeouts; i++) {
        window.clearTimeout(i);
    }
}

// Função para controlar o scroll
function controlScroll() {
    let lastScrollTop = 0;
    let isUserScrolling = false;
    
    // Previne scroll automático
    window.addEventListener('scroll', function(e) {
        if (!isUserScrolling) {
            window.scrollTo(0, lastScrollTop);
        }
    });
    
    // Marca quando o usuário está scrollando
    window.addEventListener('wheel', function() {
        isUserScrolling = true;
        lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Reseta após 1 segundo de inatividade
        setTimeout(() => {
            isUserScrolling = false;
        }, 1000);
    });
    
    // Marca quando o usuário está usando a barra de rolagem
    window.addEventListener('mousedown', function(e) {
        if (e.target.classList.contains('scrollbar') || 
            e.target.closest('.scrollbar')) {
            isUserScrolling = true;
        }
    });
}

// Função para configurar os gráficos
function setupCharts() {
    // Configurações comuns para todos os gráficos
    const commonOptions = {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    boxWidth: 12,
                    padding: 15
                }
            }
        }
    };
    
    // Aplica as configurações aos gráficos existentes
    Object.values(Chart.instances).forEach(chart => {
        chart.options = {
            ...chart.options,
            ...commonOptions
        };
        chart.update('none'); // Atualiza sem animação
    });
}

// Inicializa os controles quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    preventAutoUpdates();
    controlScroll();
    setupCharts();
    
    // Previne recarregamento automático da página
    window.addEventListener('beforeunload', function(e) {
        if (!e.target.activeElement?.closest('a, button, [type="submit"]')) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
}); 