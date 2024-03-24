// home.js
// Scripts for landing page

function setAndGetEvalRoomCookie() {
  let cookies = cookieToDict(document.cookie);

  let eval_room = cookies['evaluation_room'];
  if (eval_room === undefined) {
    eval_room = crypto.randomUUID();
    setCookie("evaluation_room", eval_room);
  }

  return eval_room
}

document.getElementById('evaluation-play-btn').addEventListener('click', function(event) {
  event.preventDefault(); // Prevent default link behavior

  // Get the evaluation_room cookie value
  const evaluationRoom = setAndGetEvalRoomCookie('evaluation_room');
  console.log("REEE")

  // If evaluation_room cookie exists, redirect to the corresponding URL
  if (evaluationRoom) {
    window.location.href = `/game/evaluation/${evaluationRoom}`;
  } else {
    alert('Cookie not found! Please allow cookies and refresh the page!');
  }
});

// The below is old code that was used for default rooms
const landingContent = document.getElementById('landing-content');
const landingForm = document.getElementById('landing-form');
const landingButton = document.getElementById('landing-btn')

function submitGamePage() {
  const loc = landingContent.value.trim();
  

  if (loc != '' && loc.match(/^[a-z0-9_-]+$/)) {
    window.location.href = "/game/" + loc;
  }
  else {
    landingContent.classList.add('is-invalid');
  }
}

landingForm.onsubmit = (e) => {
  e.preventDefault();
  e.stopPropagation();
  submitGamePage();
}

landingButton.onclick = (e) => {
  e.preventDefault();
  e.stopPropagation();
  submitGamePage();
}