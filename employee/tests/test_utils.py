"""
Utilities para testing de la app Employee.
"""
from io import BytesIO;
from PIL import Image;
from django.core.files.uploadedfile import SimpleUploadedFile;


def create_test_image(
        name='test_image.jpg',
        size=(300, 300),
        color='red',
        format='JPEG',
        content_type='image/jpeg'
):
    """
    Crea una imagen de prueba en memoria

    Args:
        name: Nombre del archivo
        size: Tupla (width, height) en pixeles
        color: Color de la imagen ('red', 'blue', 'green', etc)
        format: Formato PIL ('JPEG', 'PNG', 'WEBP')
        content_type: Content-Type del archivo

    Return:
        SimpleUploadedFile: Objeto listo para usar en tests

    Example:
        >>> image = create_test_image(200, 200)
        >>> form = EmployeeProfilePictureForm(files={'profile_picture': image})
    """
    # Crear imagen en memoria
    file_obj = BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(file_obj, format=format)
    file_obj.seek(0)

    # Convertir a UploadedFile
    return SimpleUploadedFile(
        name=name,
        content=file_obj.getvalue(),
        content_type=content_type
    )


def create_oversized_image(size_mb=3):
    """
    Crea una imagen que excede el limite de size

    Args:
        size_mb: Size aproximado en MB (default: 3MB)

    Returns:
        SimpleUploadedFile: Imagen grande para testear validacion
    """
    # Crear imagen grande(alta resolucion para que pese mas)
    # Aproximadamente: 1000x1000 RGB = ~3MB sin compresion
    dimension = int((size_mb * 1024 * 1024 / 3) ** 0.5)

    return create_test_image(
        name='overzised_image.jpg',
        size=(dimension, dimension),
        color='blue'
    )


def create_small_image(size=(100, 100)):
    """
    Crea una imagen menor a las dimensiones minimas permitidas

    Args:
        size: Tupla (width, height), default (100, 100) < 200x200 superior

    Returns:
        SimpleUploadedFile: Imagen pequenia para testear validacion
    """
    return create_test_image(
        name='small_image.jpg',
        size=size,
        color='green'
    )


def create_invalid_file(name='not_an_image.txt', content=b'This is not an image'):
    """
    Crea un archivo no valido (no es imagen)

    Args:
        name: Nombre del archivo
        content: Contenido del archivo (bytes)

    Returns:
        SimpleUploadedFile: Archivo invalido para testear validacion
    """
    return SimpleUploadedFile(
        name=name,
        content=content,
        content_type='text/plain'
    )


def get_image_info(uploaded_file):
    """
    Obtiene informacion de una imagen subida

    Args:
        uploaded_file: SimpleUploadedFile con imagen

    Returns:
        dict: {'width': int, 'height': int, 'format': str, 'size_bytes': int}
    """
    img = Image.open(uploaded_file)

    return {
        'width': img.width,
        'height': img.height,
        'format': img.format,
        'size_bytes': uploaded_file.size
    }