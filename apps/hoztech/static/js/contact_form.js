document.addEventListener('DOMContentLoaded', function() {
    const contactForm = document.getElementById('contactForm');
    const submitButton = contactForm.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    
    // Máscara para o campo de telefone
    const phoneInput = contactForm.querySelector('input[name="phone"]');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 11) value = value.slice(0, 11);
            
            if (value.length > 2) {
                value = `(${value.slice(0, 2)}) ${value.slice(2)}`;
            }
            if (value.length > 9) {
                value = `${value.slice(0, 9)}-${value.slice(9)}`;
            }
            
            e.target.value = value;
        });
    }
    
    contactForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Desabilita o botão e mostra loading
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Enviando...';
        
        try {
            // Coleta os dados do formulário
            const formData = new FormData(contactForm);
            
            // Envia a requisição
            const response = await fetch('/contact/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            // Mostra mensagem de sucesso ou erro
            if (result.success) {
                showAlert('success', result.message);
                contactForm.reset();
            } else {
                showAlert('danger', result.message);
                console.error('Detalhes do erro:', result.details);
            }
            
        } catch (error) {
            console.error('Erro ao enviar formulário:', error);
            showAlert('danger', 'Ocorreu um erro ao enviar o formulário. Por favor, tente novamente mais tarde.');
        } finally {
            // Restaura o botão
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
        }
    });
    
    function showAlert(type, message) {
        // Remove alertas anteriores
        const existingAlert = document.querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        // Cria novo alerta
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insere o alerta antes do formulário
        contactForm.parentNode.insertBefore(alertDiv, contactForm);
        
        // Remove o alerta após 5 segundos
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}); 