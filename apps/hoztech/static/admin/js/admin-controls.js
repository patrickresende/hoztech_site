// Configurações globais do DataTables
$.extend(true, $.fn.dataTable.defaults, {
    language: { url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json' },
    responsive: true,
    pageLength: 25,
    dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>rtip',
    drawCallback: function() {
        // Mantém a posição do scroll após redraw
        if (window.lastScrollPosition) {
            window.scrollTo(0, window.lastScrollPosition);
        }
    }
});

// Previne atualizações automáticas
function preventAutoUpdates() {
    // Limpa qualquer intervalo ou timeout existente
    const intervals = window.setInterval(function(){}, 9999);
    for (let i = 0; i < intervals; i++) {
        window.clearInterval(i);
    }
    
    // Previne reload automático
    window.onbeforeunload = null;
}

// Controla o comportamento do scroll
function controlScroll() {
    let isUserScrolling = false;
    
    // Registra quando o usuário está scrollando
    window.addEventListener('scroll', function() {
        isUserScrolling = true;
        window.lastScrollPosition = window.scrollY;
        
        // Reseta após 1 segundo de inatividade
        setTimeout(() => {
            isUserScrolling = false;
        }, 1000);
    });
    
    // Previne scroll automático
    window.scrollTo = function() {
        if (!isUserScrolling) {
            window.lastScrollPosition = arguments[1];
        }
        return window.scrollTo.apply(this, arguments);
    };
}

// Configura os datepickers
function setupDatePickers() {
    const dateInputs = document.querySelectorAll('.date-picker');
    dateInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Previne scroll automático ao mudar data
            window.lastScrollPosition = window.scrollY;
        });
    });
}

// Configura os tooltips
function setupTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'hover'
        });
    });
}

// Inicializa os controles quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    preventAutoUpdates();
    controlScroll();
    setupDatePickers();
    setupTooltips();
}); 