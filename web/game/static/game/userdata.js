
/**
 * Get user data from cookie
 */
function retrieveUserdata(){
  const prefs = cookieToDict(document.cookie);
  userName = prefs['user_name'];
  userID = prefs['user_id'];
  userEmail = prefs['user_email'];
  lockedOut = prefs['locked_out'] === 'true';
}

/**
 * Set cookie
 * @param {*} name 
 * @param {*} val 
 */
function setCookie(name, val){
  document.cookie = `${name}=${val}; path=/; SameSite=Strict`;
}

/**
 * Set cookie and path
 * @param {*} name 
 * @param {*} val 
 * @param {*} path 
 */
function setCookieAndPath(name, val, path){
  document.cookie = `${name}=${val}; path=${path}; SameSite=Strict`;
}

/**
 * Extract object from cookie
 * @param {*} str 
 */
function cookieToDict(str) {
    str = str.split('; ');
    let result = {};
    for (let i = 0; i < str.length; i++) {
        const cur = str[i].split('=');
        result[cur[0]] = cur[1];
    }
    return result;
}
