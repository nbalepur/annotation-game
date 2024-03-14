function updateScoreboard() {
    $('[data-toggle="popover"]').popover('hide')
    scoreboard.innerHTML = '';
    for (i = 0; i < players.length; i++) {
      const icon = document.createElement('i');
      icon.classList.add('fas');
      icon.classList.add('fa-circle');
      icon.style.margin = '0.5em';
      icon.style.color = players[i]['active'] ? '#00ff00' : '#aaaaaa';

      // Find last seen
      const lastSeenDiff = Date.now() / 1000 - new Date(players[i]['last_seen']);
      let lastSeenMessage = ''
      if (lastSeenDiff < 60) {
        lastSeenMessage = 'Now';
      } else if (lastSeenDiff < 3600) {
        lastSeenMessage = `${Math.round(lastSeenDiff / 60)} minutes ago`;
      } else if (lastSeenDiff < 86400) {
        lastSeenMessage = `${Math.round(lastSeenDiff / 3600)} hours ago`;
      } else {
        lastSeenMessage = 'Over a day ago';
      }

      const row = scoreboard.insertRow(icon);

      const playerCell = row.insertCell();
      playerCell.append(icon);
      playerCell.append(players[i]['user_name']);
      playerCell.style = 'word-break: break-all; outline: none; display: flex; align-items: center;';

      playerCell.setAttribute('tabindex', 1)
      playerCell.setAttribute('data-toggle', 'popover');
      playerCell.setAttribute('data-trigger', 'hover');
      playerCell.setAttribute('title', players[i]['user_name']);
      playerCell.setAttribute('data-content', `
        <table class="table">
          <tbody>
          <tr>
            <td>Correct</td>
            <td>${players[i]['correct']}</td>
          </tr>
          <tr>
            <td>Negs</td>
            <td>${players[i]['negs']}</td>
          </tr>
          <tr>
            <td>Last Seen</td>
            <td>${lastSeenMessage}</td>
          </tr>
        </tbody>
        </table>
      `);
      $(playerCell).popover({ html: true });

      const scoreCell = row.insertCell();
      scoreCell.append(players[i]['score']);
    }
}