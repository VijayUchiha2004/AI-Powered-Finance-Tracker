// Google OAuth
function signInWithGoogle() {
    window.location.href = '/auth/google/login';
}

// GitHub OAuth
function signInWithGithub() {
    window.location.href = '/auth/github/login';
}

// Handle form submission
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });
        
        if (response.ok) {
            window.location.href = '/dashboard';
        } else {
            const error = await response.json();
            alert(error.detail);
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Failed to login. Please try again.');
    }
});

// Show signup form
function showSignupForm() {
    // You can either redirect to a signup page or show a modal
    alert('Signup functionality coming soon!');
} 