def create_image(name: str, width: int, height: int, fb: bool):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    return bpy.data.images.new(name=name, width=width, height=height, float_buffer=fb)

def save_image(image, filepath, file_format):
    image.filepath_raw = filepath
    image.file_format = file_format
    image.save()

def link_image_to_file(image, filepath, file_format):
    """Save ``image`` to ``filepath`` and keep it linked to the file."""

    save_image(image, filepath, file_format)
    image.filepath = filepath
    try:
        image.source = 'FILE'
    except Exception:
        pass
    try:
        image.reload()
    except Exception:
        pass

def default_image_extension(image):
    name = image.name.upper()
    file_format = getattr(image, "file_format", "").upper()
    if "P" in name or file_format == "OPEN_EXR":
        return ".exr"
    if file_format == "PNG":
        return ".png"
    return ".png"

def format_bounds_suffix(pos_min, pos_max):
    def _fmt(value: float) -> str:
        return (f"{value:.3f}").rstrip("0").rstrip(".")

    return (
        f"S_{_fmt(pos_min[0])}_{_fmt(pos_min[1])}_{_fmt(pos_min[2])}_"
        f"E_{_fmt(pos_max[0])}_{_fmt(pos_max[1])}_{_fmt(pos_max[2])}"
    )