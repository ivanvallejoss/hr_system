/**
 * Profile Picture Upload - Image Preview
 * 
 * Provides client-side image preview before uploading to server.
 * Validates file type and size, displays preview with file information.
 * 
 * @requires Bootstrap 5 (for alert classes)
 */

document.addEventListener('DOMContentLoaded', function(){
    const fileInput = document.getElementById('profilePictureInput');
    const previewContainer = document.getElementById('imagePreviewContainer');
    const previewImage = document.getElementById('imagePreview');
    const imageInfo = document.getElementById('imageInfo');

    // Configuration
    const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB 
    const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

    // Validar que los elementos existen
    if (!fileInput){
        console.error('Profile picture input not found.')
        return;
    }
    
    /**
     * Valida que el archivo sea una imagen valida
     * @param {file} File - Archivo a validar
     * @returns {Object} - {valid: boolean, error:string|null}
     */
    function validateImageFile(file){
        // Validar tipo
        if (!ALLOWED_TYPES.includes(file.type)){
            return {
                valid: false,
                error: 'please select a valid image file (JPG, PNG, or WEBP)'
            };
        }

        // Validar size
        if (file.size > MAX_FILE_SIZE){
            const sizeMB = (file.size / (1024 *  1024)).toFixed(2);
            return {
                valid: false,
                error: `File is too large(${sizeMB} MB). Maximum size is 2 MB.`
            };
        }

        return {valid: true, error: null};
    }

    /**
     * Muestra el preview de la imagen seleccionada
     * @param {File} file - Archivo de una imagen
     */
    function showImagePreview(file){
        const reader = new FileReader();

        reader.onload = function(e){
            // Mostrar imagen
            previewImage.src = e.target.result;
            previewContainer.style.display = 'block';

            // Mostrar informacion del archivo
            const sizeMB = (file.size / (1024 *  1024)).toFixed(2);
            const sizeKB = (file.size / 1024).toFixed(0);

            // Elegir unidad mas apropiada
            const sizeDisplay = sizeMB >= 1
            ? `${sizeMB} MB`
            : `${sizeKB} KB`;

            imageInfo.textContent = `${file.name} (${sizeDisplay})`;

            // Validar size visualmente
            if (file.size > MAX_FILE_SIZE){
                imageInfo.innerHTML = `
                <span class="text-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    ${file.name} (${sizeMB} MB) - Too large! Maximum is 2 MB.
                </span>
                `;
            }
        };
        
        reader.onerror = function(){
            console.error('Error reading file');
            alert('Error reading file. Please try again.');
            resetPreview();
        };

        reader.readAsDataURL(file);
    }

    /**
     * Resetea el preview a su estado inicial
     */
    function resetPreview(){
        previewContainer.style.display = 'none';
        previewImage.src = '';
        imageInfo.textContent = '';
        fileInput.value = '';
    }

    /**
     * Maneja el evento de cambio en el input de archivo
     * @param {Event} e - Evento change
     */
    function handleFileChange(e){
        const file = e.target.files[0];

        if(!file){
            resetPreview();
            return;
        }

        // Validamos el archivo
        const validation = validateImageFile(file);

        if (!validation.valid){
            alert(validation.error);
            resetPreview();
            return;
        }

        // Mostrar preview
        showImagePreview(file);
    }

    // Event Listeners
    fileInput.addEventListener('change', handleFileChange);

    // Prevenir submit accidental con Enter
    fileInput.addEventListener('keypress', function(e){
        if (e.key === 'Enter'){
            e.preventDefault();
        }
    });
});