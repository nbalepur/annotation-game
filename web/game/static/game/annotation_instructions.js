document.addEventListener("DOMContentLoaded", function () {
    const iframe = document.getElementById("instruction-annotation-page");
    const savedUrl = localStorage.getItem('instructionsURL');

    const join_room_btn = document.getElementById('get-started-btn');
    join_room_btn.onclick = function () {
        joinNewRoom(savedUrl === null);
    };

    if (savedUrl) {
        iframe.src = savedUrl;
    } else {
        iframe.src = '/instructions_default'
    }
});


