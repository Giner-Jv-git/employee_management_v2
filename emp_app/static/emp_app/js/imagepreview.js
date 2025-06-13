function previewImage(input) {
    const previewContainer = input.closest('.flex').querySelector('.w-28.h-28');
    const previewText = previewContainer.querySelector('#profile-preview-text');
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            
            let img = previewContainer.querySelector('img');
            if (!img) {
                img = document.createElement('img');
                img.setAttribute('id', 'profile-preview');
                img.setAttribute('class', 'w-full h-full object-cover');
                previewContainer.innerHTML = ''; // Clear "No image" text
                previewContainer.appendChild(img);
            }
            img.src = e.target.result;
        };
        
        reader.readAsDataURL(input.files[0]);
    } else {
        
        let img = previewContainer.querySelector('img');
        if (img) {
            img.remove(); 
        }
        if (!previewText) { 
            const span = document.createElement('span');
            span.setAttribute('id', 'profile-preview-text');
            span.setAttribute('class', 'text-blue-500 text-sm text-center p-2');
            span.textContent = 'No image selected';
            previewContainer.appendChild(span);
        }
    }
}


document.addEventListener('DOMContentLoaded', function() {
    const profilePictureInput = document.getElementById('id_profile_picture');
    const previewContainer = document.querySelector('.w-28.h-28');
    
    if (profilePictureInput && previewContainer) {
        
        const existingImage = previewContainer.querySelector('img');
        if (existingImage && existingImage.src) {
            
            existingImage.setAttribute('id', 'profile-preview');
            existingImage.setAttribute('class', 'w-full h-full object-cover');
        }
    }
});