import io


class QRCode:
    def __init__(self, target_url, png_bytes=None):

        self._target_url = None
        self._png_bytes = None
        self.initialize(target_url, png_bytes)

    def initialize(self, target_url, png_bytes=None):

        self.set_target_url(target_url)
        if png_bytes is None:
            self.generate()
        else:
            self.set_png_bytes(png_bytes)

    # ---- getters ----
    def get_target_url(self):
        return self._target_url

    def get_png_bytes(self):
        return self._png_bytes

    # ---- setters ----
    def set_target_url(self, url):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError("Target URL must start with http:// or https://")
        self._target_url = url

    def set_png_bytes(self, data):
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("PNG data must be bytes.")
        self._png_bytes = bytes(data)

    # ---- behaviour ----
    def generate(self):
        import qrcode  # imported here so the class can be loaded without the library
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=10, border=4)
        qr.add_data(self._target_url)
        qr.make(fit=True)
        buffer = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
        self.set_png_bytes(buffer.getvalue())

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self._png_bytes)
