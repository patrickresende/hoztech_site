// Controles do Dashboard
(function() {
    'use strict';

    // Previne atualizações automáticas e scroll infinito
    document.addEventListener('DOMContentLoaded', function() {
        // Remove qualquer intervalo de atualização automática
        for (let i = 1; i < 99999; i++) {
            window.clearInterval(i);
        }
        
        // Remove qualquer timeout de atualização automática
        for (let i = 1; i < 99999; i++) {
            window.clearTimeout(i);
        }
        
        // Previne scroll automático
        window.scrollTo(0, 0);
        
        // Remove event listeners de scroll que possam causar comportamento indesejado
        const oldScroll = window.onscroll;
        window.onscroll = function(e) {
            // Permite apenas scroll manual
            if (e && e.isTrusted) {
                if (oldScroll) {
                    oldScroll.apply(this, arguments);
                }
            }
        };

        // Desativa qualquer atualização automática de dados
        const tables = document.querySelectorAll('.admin-table');
        tables.forEach(table => {
            // Desativa atualizações automáticas do DataTables se estiver presente
            if (table._dataTable) {
                table._dataTable.destroy();
            }

            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        // Previne atualizações automáticas da tabela
                        observer.disconnect();
                    }
                });
            });
            
            observer.observe(table, {
                childList: true,
                subtree: true
            });
        });

        // Desativa atualizações automáticas dos gráficos
        if (typeof Chart !== 'undefined') {
            Chart.defaults.animation = false;
            Chart.defaults.responsive = true;
            Chart.defaults.maintainAspectRatio = false;
            Chart.defaults.plugins.legend.display = true;
            Chart.defaults.plugins.tooltip.enabled = true;
            Chart.defaults.plugins.tooltip.intersect = false;
            Chart.defaults.plugins.tooltip.mode = 'index';
            Chart.defaults.plugins.tooltip.animation = false;
        }

        // Previne atualizações automáticas de qualquer elemento
        const preventAutoUpdates = function(element) {
            if (!element) return;
            
            // Remove event listeners que possam causar atualizações
            const clone = element.cloneNode(true);
            element.parentNode.replaceChild(clone, element);
            
            // Previne propagação de eventos
            clone.addEventListener('scroll', function(e) {
                e.stopPropagation();
            }, true);
            
            clone.addEventListener('wheel', function(e) {
                e.stopPropagation();
            }, true);
            
            clone.addEventListener('mousewheel', function(e) {
                e.stopPropagation();
            }, true);
        };

        // Aplica prevenção de atualizações em elementos específicos
        document.querySelectorAll('.admin-card, .admin-stats, .table-responsive').forEach(preventAutoUpdates);
    });

    // Previne atualizações automáticas em novos elementos adicionados ao DOM
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        node.querySelectorAll('.admin-card, .admin-stats, .table-responsive').forEach(preventAutoUpdates);
                    }
                });
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
})(); 