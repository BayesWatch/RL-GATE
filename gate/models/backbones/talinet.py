from collections import defaultdict
from typing import Any, Dict, Optional, Union

import torch
import torch.nn as nn

from tali.models import TALIModel, MultiModalityConfig


class TALINet(nn.Module):
    """
    TALINet is a multi-modal model that can process image, text, audio and video data.
    It uses separate models for each modality, and merges their outputs.
    """

    def __init__(
        self,
        clip_model_name: str = "openai/clip-vit-base-patch16",
        whisper_model_name: str = "openai/whisper-small",
    ):
        super().__init__()

        # Initialize TALIModel with specified image, text and audio models
        self.talinet = TALIModel(
            image_text_model_name=clip_model_name,
            audio_model_name=whisper_model_name,
            multi_modality_config=MultiModalityConfig(),
        )

    def forward(
        self,
        image: Optional[torch.Tensor] = None,
        text: Optional[torch.Tensor] = None,
        audio: Optional[torch.Tensor] = None,
        video: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass of the model. Processes each modality if provided, and merges the outputs.

        Args:
            image (Optional[torch.Tensor]): The image tensor.
            text (Optional[torch.Tensor]): The text tensor.
            audio (Optional[torch.Tensor]): The audio tensor.
            video (Optional[torch.Tensor]): The video tensor.

        Returns:
            Dict[str, torch.Tensor]: A dictionary containing the output tensors from each modality.
        """

        # Raise ValueError if no input modality is provided
        if image is None and text is None and audio is None and video is None:
            raise ValueError(
                f"🚫 Must provide at least one input modality to {self.__class__.__name__}."
            )

        # Process each modality and merge the outputs
        output_dict = defaultdict(dict)

        # For each modality, call the corresponding forward method and merge the results into output_dict
        # 💡 Using dictionary comprehension to simplify code and improve readability
        if image:
            output_dict |= {
                f"image_{k}": v
                for k, v in self.talinet.forward_image(image).items()
            }
        if text:
            output_dict |= {
                f"text_{k}": v
                for k, v in self.talinet.forward_text(text).items()
            }
        if audio:
            output_dict |= {
                f"audio_{k}": v
                for k, v in self.talinet.forward_audio(audio).items()
            }
        if video:
            output_dict |= {
                f"video_{k}": v
                for k, v in self.talinet.forward_video(video).items()
            }

        return output_dict