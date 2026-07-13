(function () {
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) return match[1];
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  function initFavoriteToggles() {
    document.querySelectorAll('.favorite-toggle-btn').forEach((btn) => {
      btn.addEventListener('click', function () {
        const url = btn.getAttribute('data-url');
        const icon = btn.querySelector('i');

        fetch(url, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
          },
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.favorite) {
              icon.classList.remove('bi-star');
              icon.classList.add('bi-star-fill', 'text-warning');
            } else {
              icon.classList.remove('bi-star-fill', 'text-warning');
              icon.classList.add('bi-star');
            }
          })
          .catch(() => {
            window.location.reload();
          });
      });
    });
  }

  function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('id_file');
    const fileNameLabel = document.getElementById('selected-file-name');
    if (!dropzone || !fileInput) return;

    function showFileName() {
      if (fileInput.files.length > 0) {
        fileNameLabel.textContent = fileInput.files[0].name;
      }
    }

    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', showFileName);

    ['dragenter', 'dragover'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('border-primary');
        dropzone.style.backgroundColor = 'rgba(79, 70, 229, 0.05)';
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('border-primary');
        dropzone.style.backgroundColor = '';
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        fileInput.files = files;
        showFileName();
      }
    });
  }

  function initUploadForm() {
    const form = document.getElementById('upload-form');
    if (!form) return;

    const progressWrapper = document.getElementById('upload-progress-wrapper');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressPercent = document.getElementById('upload-progress-percent');
    const errorAlert = document.getElementById('upload-error-alert');
    const submitBtn = document.getElementById('upload-submit-btn');
    const submitSpinner = document.getElementById('upload-submit-spinner');

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      errorAlert.classList.add('d-none');
      errorAlert.innerHTML = '';
      progressWrapper.classList.remove('d-none');
      submitBtn.disabled = true;
      submitSpinner.classList.remove('d-none');

      const xhr = new XMLHttpRequest();
      xhr.open('POST', form.dataset.uploadUrl, true);
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

      xhr.upload.addEventListener('progress', function (event) {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          progressBar.style.width = percent + '%';
          progressPercent.textContent = percent + '%';
        }
      });

      xhr.onload = function () {
        submitBtn.disabled = false;
        submitSpinner.classList.add('d-none');

        let data;
        try {
          data = JSON.parse(xhr.responseText);
        } catch (err) {
          data = null;
        }

        if (xhr.status >= 200 && xhr.status < 300 && data && data.success) {
          progressBar.style.width = '100%';
          progressPercent.textContent = '100%';
          window.location = data.redirect_url;
        } else {
          progressWrapper.classList.add('d-none');
          let messages = ['Upload failed. Please check the form and try again.'];
          if (data && data.errors) {
            messages = Object.values(data.errors).flat();
          }
          errorAlert.innerHTML = messages.join('<br>');
          errorAlert.classList.remove('d-none');
        }
      };

      xhr.onerror = function () {
        submitBtn.disabled = false;
        submitSpinner.classList.add('d-none');
        progressWrapper.classList.add('d-none');
        errorAlert.textContent = 'A network error occurred. Please try again.';
        errorAlert.classList.remove('d-none');
      };

      xhr.send(new FormData(form));
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initFavoriteToggles();
    initDropzone();
    initUploadForm();
  });
})();
