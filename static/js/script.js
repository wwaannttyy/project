document.addEventListener('DOMContentLoaded', function() {
    // Функция для отправки лайка
    function sendLike(profileId) {
        fetch('/like', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ profile_id: profileId }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.match) {
                alert('У вас новое совпадение!');
            }
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }

    // Добавляем обработчики событий для кнопок лайка
    const likeButtons = document.querySelectorAll('.like-button');
    likeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const profileId = this.dataset.profileId;
            sendLike(profileId);
        });
    });
});
