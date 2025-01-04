document.addEventListener("DOMContentLoaded", function () {
    const join_room_btn = document.getElementById('get-started-btn');
    join_room_btn.onclick = function () {
        joinNewRoom(false);
    };
});
