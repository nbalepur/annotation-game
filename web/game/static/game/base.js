// $(document).ready(function(){
//   load_theme();
// });

// var theme_map = {
//   "default":"https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css",
//   "darkly":"https://stackpath.bootstrapcdn.com/bootswatch/4.1.3/darkly/bootstrap.min.css",
//   "sketchy":"https://stackpath.bootstrapcdn.com/bootswatch/4.1.3/sketchy/bootstrap.min.css"
// };

// $('#theme-select').change(function(e) {
//   change_theme();
// });

// // changes bootswatch theme
// function change_theme(){
//   $('#theme-stylesheet').attr('href', theme_map[$('#theme-select').val()]);
//   setCookieAndPath('theme', $('#theme-select').val(), '/');
// }

// // loads theme from cookies
// function load_theme(){
//   var prefs = cookieToDict(document.cookie);
//   if(prefs['theme'] != undefined){
//     $('#theme-select').val(prefs['theme']);
//     $('#theme-stylesheet').attr('href', theme_map[$('#theme-select').val()]);
//   }
// }
