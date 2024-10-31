const profileIcon = document.getElementById('profile-icon');
const historyIcon = document.getElementById('history-icon');
const betIcon = document.getElementById('bet-icon');

if (window.location.href.indexOf('profile') > -1) {
    profileIcon.classList.add('active');
  }
  
  if (window.location.href.indexOf('bet') > -1) {
    betIcon.classList.add('active');
  }
  
  if (window.location.href.indexOf('history') > -1) {
    historyIcon.classList.add('active');
  }



  