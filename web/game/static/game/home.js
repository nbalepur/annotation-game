// home.js
// Scripts for landing page

function uuidv4() {
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
    (+c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> +c / 4).toString(16)
  );
}

function getRandomElement(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function setAndGetEvalRoomCookie(roomName) {
  // let cookies = cookieToDict(document.cookie);

  // let eval_room = cookies['evaluation_room'];
  // if (eval_room === undefined) {
  //   eval_room = uuidv4();
  //   setCookie("evaluation_room", eval_room);
  // }

  if (roomName !== "") {
    return roomName.replace(/[^a-zA-Z0-9-_]/g, '').toLowerCase();
  }

  const adjectives = ["wift", "Clever", "Brave", "Bold", "Happy", "Curious", "Witty"];
  const nouns = ["Tiger", "Phoenix", "Eagle", "Shark", "Panther", "Falcon", "Lion"];
  const colors = ["Red", "Blue", "Green", "Yellow", "Purple", "Black", "White"];

  const randomAdjective = getRandomElement(adjectives);
  const randomNoun = getRandomElement(nouns);
  const randomColor = getRandomElement(colors);
  const randomRoom = `${randomAdjective}${randomColor}${randomNoun}`;
  return randomRoom.replace(/[^a-zA-Z0-9-_]/g, '').toLowerCase();
}

function sleep(ms = 0) {
  return new Promise(resolve => setTimeout(resolve, ms));
}


document.getElementById('evaluation-play-btn').addEventListener('click', function(event) {
  console.log('hi');
  event.preventDefault();
  const roomName = document.getElementById('new-room-name').value;
  const evaluationRoom = setAndGetEvalRoomCookie(roomName);
  if (evaluationRoom) {
    window.location.href = `/game/evaluation/${evaluationRoom}`;
  } else {
    alert('Please enter a valid room name!');
  }
});

// The below is old code that was used for default rooms
const landingContent = document.getElementById('landing-content');
// const landingForm = document.getElementById('landing-form');
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

// landingForm.onsubmit = (e) => {
//   e.preventDefault();
//   e.stopPropagation();
//   submitGamePage();
// }

landingButton.onclick = (e) => {
  e.preventDefault();
  e.stopPropagation();
  submitGamePage();
}