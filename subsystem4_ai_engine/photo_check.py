"""PhotoCheck: checks an uploaded photo before the AI looks at it, and deletes it afterwards."""
from pathlib import Path

from PIL import Image

from .errors import InvalidPhotoError


class PhotoCheck:
    def __init__(self, max_megabytes=10):
        self._max_megabytes = max_megabytes
        self._allowed_formats = []
        self.initialize()

    def initialize(self):
        """Set the photo formats we accept."""
        self._allowed_formats = ["JPEG", "PNG"]

    def get_max_megabytes(self):
        return self._max_megabytes

    def set_max_megabytes(self, max_megabytes):
        self._max_megabytes = max_megabytes

    def get_allowed_formats(self):
        return self._allowed_formats

    def set_allowed_formats(self, allowed_formats):
        self._allowed_formats = allowed_formats

    def check(self, photo_path):
        """Raise InvalidPhotoError if the photo is too big, or is not a JPG or PNG."""
        size_in_megabytes = Path(photo_path).stat().st_size / (1024 * 1024)
        if size_in_megabytes > self._max_megabytes:
            raise InvalidPhotoError(f"The photo is bigger than {self._max_megabytes} MB.")

        # Open the file to see what it really is. A renamed .txt file is not a photo.
        try:
            with Image.open(photo_path) as image:
                photo_format = image.format
        except OSError:
            raise InvalidPhotoError("The file is not a photo.")

        if photo_format not in self._allowed_formats:
            raise InvalidPhotoError("Only JPG and PNG photos are accepted.")

    def delete(self, photo_path):
        """Delete the photo from the disk."""
        Path(photo_path).unlink(missing_ok=True)
