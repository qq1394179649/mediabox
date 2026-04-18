// Emby管理系统 - 前端交互脚本（性能优化版）
'use strict';

document.addEventListener('DOMContentLoaded', function() {
    // 自动关闭Flash消息
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.4s';
            alert.style.opacity = '0';
            setTimeout(function() { alert.remove(); }, 400);
        }, 4000);
    });

    // 确认删除操作
    document.querySelectorAll('[data-confirm]').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || '确认执行此操作？')) {
                e.preventDefault();
                e.stopImmediatePropagation();
            }
        });
    });

    // 图片懒加载（IntersectionObserver）
    if ('IntersectionObserver' in window) {
        var lazyImages = document.querySelectorAll('img[loading="lazy"]');
        var imgObserver = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    var img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    imgObserver.unobserve(img);
                }
            });
        }, { rootMargin: '100px' });
        lazyImages.forEach(function(img) { imgObserver.observe(img); });
    }
});

// 发送会话消息
function sendMessage(sessionId) {
    var modal = document.getElementById('message-modal');
    if (modal) {
        modal.style.display = 'flex';
        var form = document.getElementById('message-form');
        if (form) form.action = '/sessions/' + sessionId + '/message';
    }
}

function closeModal(modalId) {
    var modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('open');
}
