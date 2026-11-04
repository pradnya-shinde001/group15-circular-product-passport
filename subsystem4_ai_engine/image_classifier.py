"""Identify a product from a photo with zero-shot CLIP (no training data needed). No photo is sent to the LLM."""
from io import BytesIO

from PIL import Image

from .ai_prediction import AIPrediction

MODEL_NAME = "openai/clip-vit-base-patch32"
MODEL_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"  # pinned, so results stay comparable and the log names the exact version
MAX_PHOTO_BYTES = 10 * 1024 * 1024
UNCERTAIN_BELOW = 0.30
TOP_K = 3

CATEGORIES = {
    "Laptop": "a photo of a laptop computer",
    "Smartphone": "a photo of a smartphone",
    "Tablet": "a photo of a tablet computer",
    "Monitor": "a photo of a computer monitor",
    "Desktop computer": "a photo of a desktop computer tower",
    "Printer": "a photo of a printer",
    "Keyboard": "a photo of a computer keyboard",
    "Headphones": "a photo of headphones",
    "Smartwatch": "a photo of a smartwatch",
    "Camera": "a photo of a digital camera",
}

MATERIALS = {
    "Plastic": "an electronic device with a plastic body",
    "Aluminium": "an electronic device with an aluminium metal body",
    "Glass": "an electronic device with a glass surface",
    "Steel": "an electronic device with a stainless steel body",
    "Rubber": "an electronic device made of soft rubber",
    "Fabric": "an electronic device covered in fabric",
}


class PhotoError(Exception):
    pass


def load_photo(data):
    """Return (RGB image, format). Raises PhotoError unless `data` is a real JPG/PNG up to 10 MB."""
    if len(data) > MAX_PHOTO_BYTES:
        raise PhotoError(f"The photo is {len(data) / 1024 / 1024:.1f} MB. The limit is 10 MB.")
    try:
        # The content decides the format, so a renamed file is rejected too.
        image = Image.open(BytesIO(data), formats=["JPEG", "PNG"])
        fmt = image.format
        return image.convert("RGB"), fmt
    except (OSError, ValueError, Image.DecompressionBombError) as e:
        raise PhotoError("This file is not a readable JPG or PNG image.") from e


class ImageClassifier:
    def __init__(self, model_name=MODEL_NAME, revision=MODEL_REVISION, uncertain_below=UNCERTAIN_BELOW, top_k=TOP_K):
        self.model_name = model_name
        self.revision = revision
        self.uncertain_below = uncertain_below
        self.top_k = top_k

    def initialize(self):
        """Load CLIP on first use, because it is slow and the rest of the code does not need it."""
        if self._model is not None:
            return
        import transformers
        model = transformers.CLIPModel.from_pretrained(self._model_name, revision=self._revision)
        self._processor = transformers.CLIPProcessor.from_pretrained(self._model_name, revision=self._revision)
        model.eval()
        self._model = model

    @property
    def model_name(self):
        return self._model_name

    @model_name.setter
    def model_name(self, value):
        if not value:
            raise ValueError("model_name is required.")
        self._model_name = value
        self._unload()

    @property
    def revision(self):
        return self._revision

    @revision.setter
    def revision(self, value):
        if not value:
            raise ValueError("revision is required.")
        self._revision = value
        self._unload()

    @property
    def uncertain_below(self):
        return self._uncertain_below

    @uncertain_below.setter
    def uncertain_below(self, value):
        if not 0 <= value <= 1:
            raise ValueError("uncertain_below must be between 0 and 1.")
        self._uncertain_below = value

    @property
    def top_k(self):
        return self._top_k

    @top_k.setter
    def top_k(self, value):
        if not isinstance(value, int) or value < 1:
            raise ValueError("top_k must be a whole number of at least 1.")
        self._top_k = value

    @property
    def is_loaded(self):
        return self._model is not None

    def _unload(self):
        """A different model or revision must be loaded again on the next classify()."""
        self._model = None
        self._processor = None

    def _scores(self, image, texts):
        """Probability of each text for the image; the probabilities sum to 1."""
        import torch
        self.initialize()
        inputs = self._processor(text=texts, images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = self._model(**inputs).logits_per_image[0]
        return logits.softmax(dim=0).tolist()

    def _top(self, image, labels):
        scores = self._scores(image, list(labels.values()))
        ranked = sorted(zip(labels, scores), key=lambda pair: pair[1], reverse=True)[:self._top_k]
        return [{"label": label, "confidence": round(score, 3), "uncertain": score < self._uncertain_below}
                for label, score in ranked]

    def classify(self, photo):
        """Top-3 categories and materials for a photo."""
        image, _ = load_photo(photo)
        result = {"category": self._top(image, CATEGORIES), "material": self._top(image, MATERIALS)}
        return AIPrediction("identification", result, self._model_name, self._revision)
