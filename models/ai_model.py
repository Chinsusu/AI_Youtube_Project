from typing import Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
from torchvision.models import resnet18, ResNet18_Weights


class AIModel:
    """
    Simple image classifier using torchvision's pretrained ResNet18.
    Designed for CPU inference and small demo workloads.
    """

    def __init__(self) -> None:
        self.device = torch.device("cpu")
        # Prefer DEFAULT which tracks the recommended pretrained weights
        self.weights = ResNet18_Weights.DEFAULT
        self.model = resnet18(weights=self.weights)
        self.model.eval()
        self.model.to(self.device)

        # Use official transforms bundled with the weights to avoid meta mismatches
        self.preprocess = self.weights.transforms()
        self.categories = self.weights.meta.get("categories", [])

    @torch.inference_mode()
    def predict(self, frame_bgr: np.ndarray) -> Tuple[str, float]:
        """
        Run classification on a BGR image (numpy array) and return (label, prob).
        """
        # Convert BGR->RGB
        frame_rgb = frame_bgr[:, :, ::-1]
        image = Image.fromarray(frame_rgb)
        tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        logits = self.model(tensor)
        probs = F.softmax(logits, dim=1)[0]
        prob, idx = torch.max(probs, dim=0)
        label = self.categories[idx.item()]
        return label, float(prob.item())
