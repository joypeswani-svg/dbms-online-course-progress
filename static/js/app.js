// LearnPulse SaaS Global App Scripts

document.addEventListener('alpine:init', () => {
  // 1. Toast Notification Store
  Alpine.store('toasts', {
    items: [],
    add(message, type = 'success', title = '') {
      const id = Date.now() + Math.random();
      const toast = { id, message, type, title };
      this.items.push(toast);
      setTimeout(() => {
        this.remove(id);
      }, 4500);
    },
    remove(id) {
      this.items = this.items.filter(t => t.id !== id);
    }
  });

  // 2. Global Delete Modal Store
  Alpine.store('deleteModal', {
    isOpen: false,
    title: 'Confirm Deletion',
    message: 'Are you sure you want to delete this record? This action cannot be undone.',
    actionUrl: '',
    confirmText: 'Delete Record',
    open(url, title, message) {
      this.actionUrl = url;
      if (title) this.title = title;
      if (message) this.message = message;
      this.isOpen = true;
    },
    close() {
      this.isOpen = false;
      this.actionUrl = '';
    }
  });

  // 3. Theme Store
  Alpine.store('theme', {
    dark: localStorage.getItem('learnpulse_theme') !== 'light',
    init() {
      this.apply();
    },
    toggle() {
      this.dark = !this.dark;
      localStorage.setItem('learnpulse_theme', this.dark ? 'dark' : 'light');
      this.apply();
    },
    apply() {
      if (this.dark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      // Re-render chart defaults if chart exists
      window.dispatchEvent(new CustomEvent('theme-changed', { detail: { dark: this.dark } }));
    }
  });

  // 4. Admin Password Modal Store
  Alpine.store('adminModal', {
    isOpen: false,
    password: '',
    showPassword: false,
    errorMessage: '',
    shaking: false,
    loading: false,
    locked: false,
    lockoutSeconds: 0,
    timerInterval: null,
    open() {
      this.isOpen = true;
      this.password = '';
      this.showPassword = false;
      this.errorMessage = '';
      this.shaking = false;
      this.loading = false;
      this.$nextTick && this.$nextTick(() => {
        const inp = document.getElementById('admin-password-input');
        if (inp) inp.focus();
      });
    },
    close() {
      this.isOpen = false;
      this.password = '';
      this.errorMessage = '';
      this.shaking = false;
    },
    toggleShowPassword() {
      this.showPassword = !this.showPassword;
    },
    startLockout(seconds) {
      this.locked = true;
      this.lockoutSeconds = seconds;
      if (this.timerInterval) clearInterval(this.timerInterval);
      this.timerInterval = setInterval(() => {
        this.lockoutSeconds--;
        if (this.lockoutSeconds <= 0) {
          clearInterval(this.timerInterval);
          this.locked = false;
          this.errorMessage = '';
        }
      }, 1000);
    },
    async submit() {
      if (this.locked) return;
      if (!this.password) {
        this.triggerError('Please enter the admin password.');
        return;
      }
      this.loading = true;
      this.errorMessage = '';
      try {
        const res = await fetch('/auth/admin-unlock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: this.password })
        });
        const data = await res.json();
        this.loading = false;
        if (res.ok && data.success) {
          this.close();
          window.showToast(data.message || 'Admin mode on', 'success');
          setTimeout(() => {
            window.location.href = data.redirect || '/admin';
          }, 350);
        } else {
          if (data.locked) {
            this.startLockout(data.lockout_seconds || 30);
            this.triggerError(data.error || 'Too many failed attempts. Form locked for 30 seconds.');
          } else {
            this.triggerError(data.error || 'Incorrect password. Try again.');
          }
        }
      } catch (err) {
        this.loading = false;
        this.triggerError('Unable to connect to server. Please try again.');
      }
    },
    triggerError(msg) {
      this.errorMessage = msg;
      this.shaking = true;
      setTimeout(() => {
        this.shaking = false;
      }, 500);
    }
  });

  // 5. Instructor Password Modal Store
  Alpine.store('instructorModal', {
    isOpen: false,
    instructorId: 'I02',
    password: '',
    showPassword: false,
    errorMessage: '',
    shaking: false,
    loading: false,
    locked: false,
    lockoutSeconds: 0,
    timerInterval: null,
    open() {
      this.isOpen = true;
      this.password = '';
      this.showPassword = false;
      this.errorMessage = '';
      this.shaking = false;
      this.loading = false;
      this.$nextTick && this.$nextTick(() => {
        const inp = document.getElementById('instructor-password-input');
        if (inp) inp.focus();
      });
    },
    close() {
      this.isOpen = false;
      this.password = '';
      this.errorMessage = '';
      this.shaking = false;
    },
    toggleShowPassword() {
      this.showPassword = !this.showPassword;
    },
    startLockout(seconds) {
      this.locked = true;
      this.lockoutSeconds = seconds;
      if (this.timerInterval) clearInterval(this.timerInterval);
      this.timerInterval = setInterval(() => {
        this.lockoutSeconds--;
        if (this.lockoutSeconds <= 0) {
          clearInterval(this.timerInterval);
          this.locked = false;
          this.errorMessage = '';
        }
      }, 1000);
    },
    async submit() {
      if (this.locked) return;
      if (!this.password) {
        this.triggerError('Please enter the instructor password.');
        return;
      }
      this.loading = true;
      this.errorMessage = '';
      try {
        const res = await fetch('/auth/instructor-unlock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: this.password, instructor_id: this.instructorId })
        });
        const data = await res.json();
        this.loading = false;
        if (res.ok && data.success) {
          this.close();
          window.showToast(data.message || 'Instructor mode on', 'success');
          setTimeout(() => {
            window.location.href = data.redirect || '/instructor/dashboard';
          }, 350);
        } else {
          if (data.locked) {
            this.startLockout(data.lockout_seconds || 30);
            this.triggerError(data.error || 'Too many failed attempts. Form locked for 30 seconds.');
          } else {
            this.triggerError(data.error || 'Incorrect instructor password. Try again.');
          }
        }
      } catch (err) {
        this.loading = false;
        this.triggerError('Unable to connect to server. Please try again.');
      }
    },
    triggerError(msg) {
      this.errorMessage = msg;
      this.shaking = true;
      setTimeout(() => {
        this.shaking = false;
      }, 500);
    }
  });
});

// Helper function to trigger toasts easily from vanilla JS
window.showToast = function(message, type = 'success', title = '') {
  if (window.Alpine && Alpine.store('toasts')) {
    Alpine.store('toasts').add(message, type, title);
  }
};

// Re-run Lucide icons on DOM updates
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }
});
