"""ImageClassifier: guesses what a product photo shows, with the CLIP model.

CLIP compares the photo with short sentences such as "a photo of a laptop" and says how well
each one fits. This is called zero-shot: we never trained it on our own products.
The model (about 600 MB) is downloaded the first time it is loaded."""
import threading

from PIL import Image

CATEGORIES = ["Laptop", "Smartphone", "Tablet", "Monitor", "Desktop computer", "Printer",
              "Keyboard", "Headphones", "Smartwatch", "Camera"]
MATERIALS = ["Aluminium", "Plastic", "Glass", "Copper", "Steel", "Rubber"]
RECYCLABLE_MATERIALS = ["Aluminium", "Plastic", "Glass", "Copper", "Steel"]  # the same as in database/seed.py


class ImageClassifier:
    def __init__(self, model_name="openai/clip-vit-base-patch32", uncertain_below=0.30):
        self._model_name = model_name
        self._uncertain_below = uncertain_below
        self._categories = []
        self._materials = []
        self._model = None
        self._processor = None
        self._lock = None
        self.initialize()

    def initialize(self):
        """Set the categories and materials CLIP chooses from."""
        self._categories = list(CATEGORIES)
        self._materials = list(MATERIALS)
        self._lock = threading.Lock()  # so CLIP is never loaded twice at the same time

    def is_loaded(self):
        return self._model is not None

    def get_model_name(self):
        return self._model_name

    def set_model_name(self, model_name):
        self._model_name = model_name

    def get_uncertain_below(self):
        return self._uncertain_below

    def set_uncertain_below(self, uncertain_below):
        self._uncertain_below = uncertain_below

    def get_categories(self):
        return self._categories

    def set_categories(self, categories):
        self._categories = categories

    def get_materials(self):
        return self._materials

    def set_materials(self, materials):
        self._materials = materials

    def classify(self, photo_path):
        """Return the top 3 categories and the top 3 materials for one photo."""
        with Image.open(photo_path) as photo:
            image = photo.convert("RGB")

        category_sentences = [f"a photo of a {name.lower()}" for name in self._categories]
        material_sentences = [f"a product made of {name.lower()}" for name in self._materials]

        return {"categories": self.top_predictions(self._categories, self._ask_clip(image, category_sentences)),
                "materials": self.top_predictions(self._materials, self._ask_clip(image, material_sentences)),
                "model": self._model_name}

    def top_predictions(self, labels, confidences, top=3):
        """The `top` best labels, best first. Below 30 % confidence a label is marked uncertain."""
        pairs = sorted(zip(labels, confidences), key=lambda pair: pair[1], reverse=True)
        results = []
        for label, confidence in pairs[:top]:
            results.append({"label": label,
                            "confidence": round(confidence, 2),
                            "uncertain": confidence < self._uncertain_below})
        return results

    def _ask_clip(self, image, sentences):
        """How well each sentence fits the photo. The numbers add up to 1."""
        import torch  # imported here, so the rest of the app starts fast without the big AI libraries

        self.load()
        inputs = self._processor(text=sentences, images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self._model(**inputs)
        return outputs.logits_per_image.softmax(dim=1)[0].tolist()

    def load(self):
        """Load CLIP once. The app calls this when it starts, so the first photo is fast too (NFR 2).
        If a photo comes in while CLIP is still loading, it waits here until loading is done."""
        with self._lock:
            if self._model is None:
                from transformers import CLIPModel, CLIPProcessor
                self._model = CLIPModel.from_pretrained(self._model_name)
                self._processor = CLIPProcessor.from_pretrained(self._model_name)
