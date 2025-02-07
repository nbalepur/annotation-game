document.addEventListener('DOMContentLoaded', function () {
  const stepOne = document.getElementById('step-one');
  const loginForm = document.getElementById('login-form');
  const loginFields = document.getElementById('login-fields');
  const registerFields = document.getElementById('register-fields');
  const forgotPasswordForm = document.getElementById('forgot-password-form');
  const modalTitle = document.getElementById('modal-title');

  const loginStatus = document.getElementById('login-status-text');
  const loginStatusWrapper = document.getElementById('login-status-text-wrapper');

  if (!document.getElementById('choose-login')) {
    return;
  }

  // Transition to Login Form
  document.getElementById('choose-login').addEventListener('click', () => {
      stepOne.style.display = 'none';
      loginForm.style.display = 'block';
      loginFields.style.display = 'block';
      registerFields.style.display = 'none';
      forgotPasswordForm.style.display = 'none';
      modalTitle.textContent = 'Log In to Your Account';
      loginStatusWrapper.style.display = 'none';
  });

  // Transition to Register Form
  document.getElementById('choose-register').addEventListener('click', () => {
      stepOne.style.display = 'none';
      loginForm.style.display = 'block';
      loginFields.style.display = 'none';
      registerFields.style.display = 'block';
      forgotPasswordForm.style.display = 'none';
      modalTitle.textContent = 'Create a New Account';
      loginStatusWrapper.style.display = 'none';
  });

  // Transition to Forgot Password Form
  document.getElementById('forgot-password-link').addEventListener('click', (event) => {
      event.preventDefault();
      loginFields.style.display = 'none';
      registerFields.style.display = 'none';
      forgotPasswordForm.style.display = 'block';
      modalTitle.textContent = 'Reset Your Password';
      loginStatusWrapper.style.display = 'none';
  });

  // Back to Login from Forgot Password
  document.getElementById('back-to-login').addEventListener('click', (event) => {
      event.preventDefault();
      forgotPasswordForm.style.display = 'none';
      loginFields.style.display = 'block';
      modalTitle.textContent = 'Log In to Your Account';
      loginStatusWrapper.style.display = 'none';
  });

  // Back to Main Selection
  document.querySelectorAll('#back-to-main, #back-to-main2').forEach((btn) => {
      btn.addEventListener('click', (event) => {
          event.preventDefault();
          stepOne.style.display = 'block';
          loginForm.style.display = 'none';
          registerFields.style.display = 'none';
          forgotPasswordForm.style.display = 'none';
          modalTitle.textContent = 'Welcome to Planorama!';
          loginStatusWrapper.style.display = 'none';
      });
  });

  // Login Submission
  document.getElementById('login-submit').addEventListener('click', function (event) {
      event.preventDefault();
      const identifier = document.getElementById('login-identifier').value.trim();
      const password = document.getElementById('login-password').value.trim();

      fetch('/login/', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCookie('csrftoken'),
              
          },
          credentials: 'include',
          body: JSON.stringify({ identifier, password }),
      })
          .then((response) => {return response.json();})
          .then((data) => {
              if (data.success) {
                location.reload();
              } else {
                loginStatusWrapper.style.display = '';
                loginStatus.textContent = data.message;
              }
          })
          .catch((error) => console.error('Error:', error));
  });

  // Register Submission
  document.getElementById('register-submit').addEventListener('click', function (event) {
      event.preventDefault();

      const email = document.getElementById('register-email').value.trim();
      const username = document.getElementById('register-username').value.trim();
      const password = document.getElementById('register-password').value.trim();

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
          loginStatus.textContent = 'Please enter a valid email address.';
          loginStatusWrapper.style.display = '';
          return;
      }
      if (username.length < 1) {
          loginStatus.textContent = 'Username cannot be empty.';
          loginStatusWrapper.style.display = '';
          return;
      }
      const usernameRegex = /^[a-zA-Z0-9_.]+$/;
      if (!usernameRegex.test(username)) {
          loginStatus.textContent = 'Username can only contain letters, numbers, underscores, and periods, and cannot include spaces.';
          loginStatusWrapper.style.display = '';
          return;
      }
      if (password.length < 1) {
          loginStatus.textContent = 'Password cannot be empty.';
          loginStatusWrapper.style.display = '';
          return;
      }
      if (/\s/.test(password)) {
        loginStatus.textContent = 'Password cannot contain spaces.';
        loginStatusWrapper.style.display = '';
        return;
      }

      fetch('/register/', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCookie('csrftoken'),
          },
          credentials: 'include',
          body: JSON.stringify({ email, username, password }),
      })
          .then((response) => {return response.json();})
          .then((data) => {
              if (data.success) {
                location.reload();
              } else {
                loginStatus.textContent = data.message;
                loginStatusWrapper.style.display = '';
              }
          })
          .catch((error) => console.error('Error:', error));
  });

  // Forgot Password Submission
  document.getElementById('forgot-password-submit').addEventListener('click', function (event) {
      event.preventDefault();

      const email = document.getElementById('forgot-password-email').value.trim();
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      if (!emailRegex.test(email)) {
          loginStatus.textContent = 'Please enter a valid email address.';
          loginStatusWrapper.style.display = '';
          return;
      }

      fetch('/reset-password/', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCookie('csrftoken'),
          },
          credentials: 'include',
          body: JSON.stringify({ email: email })
      })
          .then((response) => {return response.json();})
          .then((data) => {
              if (data.success) {
                  loginStatus.textContent = data.message;
                  loginStatusWrapper.style.display = '';
                  forgotPasswordForm.style.display = 'none';
                  loginFields.style.display = 'block';
                  modalTitle.textContent = 'Log In to Your Account';
              } else {
                loginStatus.textContent = data.message;
                loginStatusWrapper.style.display = '';
                loginStatusWrapper.style.display = '';
              }
          }).catch((error) => console.log('Error:', error));
  });

  // Helper function to get CSRF token
  function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
          const cookies = document.cookie.split(';');
          for (let i = 0; i < cookies.length; i++) {
              const cookie = cookies[i].trim();
              if (cookie.startsWith(name + '=')) {
                  cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                  break;
              }
          }
      }
      return cookieValue;
  }
});
