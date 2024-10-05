function updateMessages() {
    messageSpace.innerHTML = '';
    for (i = 0; i < Math.min(10, messages.length); i++) {
      const icon = document.createElement('i');
      let msgHTML;

      icon.style.margin = '0.5em';
      switch (messages[i]['tag']) {
        case "buzz_init":
          icon.classList.add('fa-regular');
          icon.classList.add('fa-bell');
          break;
        case "buzz_correct":
          icon.classList.add('fa-solid');
          icon.classList.add('fa-circle-check');
          break;
        case "buzz_wrong":
          icon.classList.add('fa-solid');
          icon.classList.add('fa-circle-xmark');
          break;
        case "chat":
          icon.classList.add('fa-regular');
          icon.classList.add('fa-comment-alt');
          break;
        case "leave":
          icon.classList.add('fas');
          icon.classList.add('fa-door-open');
          break;
        case "join":
          icon.classList.add('fas');
          icon.classList.add('fa-sign-in-alt');
          break;
        default:
          icon.classList.add('far');
          icon.classList.add('fa-circle');
          icon.style.opacity = 0;
          break;
      }

      switch (messages[i]['tag']) {
        case "join":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> joined`;
          break;
        case "leave":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> left`;
          break;
        case "buzz_init":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> buzzed`;
          break;
        case "buzz_correct":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> correctly answered <strong>${messages[i]['content']}</strong>`;
          break;
        case "buzz_wrong":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> incorrectly answered <strong>${messages[i]['content']}</strong>`;
          break;
        case "buzz_forfeit":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> failed to buzz`;
          break;
        case "set_category":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> changed the category to <strong>${messages[i]['content']}</strong>`;
          break;
        case "set_difficulty":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> changed the difficulty to <strong>${messages[i]['content']}</strong>`;
          break;
        case "reset_score":
          msgHTML = `<strong>${messages[i]['user_name']}</strong> reset their score`;
          break;
        case "chat":
          msgHTML = `<strong>${messages[i]['user_name']}</strong>: ${messages[i]['content']}`;
          break;
      }

      const msg = document.createElement('div');
      msg.innerHTML = msgHTML;

      const leftSide = document.createElement('div');
      leftSide.style.display = 'flex';
      leftSide.style.alignItems = 'center';
      leftSide.append(icon);
      leftSide.append(msg);

      const messageID = messages[i]['message_id'];
      // const reportBtn = document.createElement('div');
      // reportBtn.title = 'Flag as inappropriate'
      // reportBtn.className = 'btn btn-sm';
      // reportBtn.innerHTML = `<i class="fas fa-flag" style="color: gray;"></i>`;
      // reportBtn.onclick = () => {
      //   const res = confirm('Report the player that wrote this message?');
      //   if (res) {
      //     reportMessage(messageID);
      //   }
      // }

      const li = document.createElement('li');
      li.classList.add('list-group-item');
      li.style.display = 'flex';
      li.style.justifyContent = 'space-between';
      li.style.alignItems = 'center';
      li.append(leftSide);

      if (messages[i]['tag'] === 'chat' ||
        messages[i]['tag'] === 'buzz_correct' ||
        messages[i]['tag'] === 'buzz_wrong') {
        // li.append(reportBtn);
      }

      messageSpace.append(li);
    }
}