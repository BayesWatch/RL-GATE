import logging
from typing import Dict, Optional

import torch
import torch.nn as nn
from transformers import (
    BartConfig,
    BartPreTrainedModel,
    CLIPModel,
    CLIPProcessor,
)
from transformers.models.bart.modeling_bart import BartEncoder

from gate.boilerplate.decorators import configurable
from gate.models.backbones import (
    GATEncoder,
    Modality,
    TextProcessor,
    VisionTextGATEAdapter,
    forward_dict,
)
from gate.models.core import reinit
from gate.models.task_adapters.utils.modality_transfer import (
    VisionRootReplacedBackbone,
)

logger = logging.getLogger(__name__)


class ModifiedBartModel(BartPreTrainedModel):
    def __init__(self, config: BartConfig):
        super().__init__(config)

        padding_idx, vocab_size = config.pad_token_id, config.vocab_size

        self.shared = nn.Embedding(vocab_size, config.d_model, padding_idx)

        self.encoder = BartEncoder(config, self.shared)

        # Initialize weights and apply final processing
        self.post_init()

    def forward(
        self,
        image: Optional[torch.Tensor],
    ) -> Dict[str, torch.Tensor]:
        # different to other models, Bart automatically creates decoder_input_ids from
        # input_ids if no decoder_input_ids are provided
        encoder_outputs = self.encoder(
            input_ids=None,
            attention_mask=None,
            head_mask=None,
            inputs_embeds=image,
            output_attentions=None,
            output_hidden_states=True,
            return_dict=True,
        )

        return {
            "features": encoder_outputs.last_hidden_state.mean(dim=1),
            "raw_features": encoder_outputs.last_hidden_state,
            "per_layer_raw_features": encoder_outputs.hidden_states,
        }


class CLIPModelPaths:
    laion_b_16: str = "laion/CLIP-ViT-B-16-laion2B-s34B-b88K"
    openai_b_16: str = "openai/clip-vit-base-patch16"


class BartModelPaths:
    base: str = "facebook/bart-base"


@configurable(
    group="encoder",
    name="bart",
)
class BartAdapter(VisionTextGATEAdapter, GATEncoder):
    def __init__(
        self,
        clip_model_name: str = CLIPModelPaths.openai_b_16,
        bart_model_name: str = BartModelPaths.base,
        pretrained: bool = True,
        image_size: Optional[int] = None,
        num_projection_features: Optional[int] = None,
    ):
        VisionTextGATEAdapter.__init__(self)
        nn.Module.__init__(self)
        self.image_size = image_size
        self.preprocessor: CLIPProcessor = CLIPProcessor.from_pretrained(
            clip_model_name
        )
        self.clip = CLIPModel.from_pretrained(clip_model_name)
        self.text_transforms = TextProcessor(self.preprocessor)

        if not pretrained:
            self.clip.init_weights()

        vision_embedding = ModifiedBartModel.from_pretrained(
            bart_model_name,
            max_position_embeddings=(
                4097
                if image_size == 1024
                else 2049 if image_size == 512 else 1025
            ),
            ignore_mismatched_sizes=True,
        )

        self.vision_model = VisionRootReplacedBackbone(
            model=vision_embedding,
            num_root_features=vision_embedding.config.hidden_size,
            backbone_root_layers_to_remove=["embeddings"],
            image_size=image_size,
            num_channels=3,
            patch_size=16,
            source_modality=Modality.image,
            target_modality=Modality.image,
        )
        self.visual_projection = (
            nn.Linear(
                vision_embedding.config.hidden_size,
                num_projection_features,
                bias=False,
            )
            if num_projection_features is not None
            else nn.Identity()
        )

        self.text_model = self.clip.text_model
        self.text_projection = (
            nn.Linear(
                self.text_model.config.hidden_size,
                num_projection_features,
            )
            if num_projection_features is not None
            else nn.Identity()
        )
        self.text_num_raw_features = self.text_model.config.hidden_size
        self.image_num_raw_features = vision_embedding.config.hidden_size

        # setattr signature: setattr(object, name, value)

        setattr(self.vision_model, "legacy_forward", self.text_model.forward)
        setattr(self.text_model, "legacy_forward", self.text_model.forward)

        setattr(
            self.text_model, "forward", forward_dict.__get__(self.text_model)
        )

        self.image_num_features = (
            self.clip.vision_embed_dim
            if num_projection_features is None
            else num_projection_features
        )
        self.text_num_features = (
            self.clip.text_embed_dim
            if num_projection_features is None
            else num_projection_features
        )

    @property
    def image_shape(self):
        return (self.image_size, self.image_size)

    def init_weights(self):
        reinit(self)

    @property
    def num_in_features_image(self):
        return self.image_num_features

    @property
    def num_raw_features_image(self):
        return self.image_num_raw_features

    @property
    def num_raw_features_text(self):
        return self.text_num_raw_features

    @property
    def num_in_features_text(self):
        return self.text_num_features

    @property
    def num_in_features_video(self):
        raise NotImplementedError("BART does not have a video backbone")

    def init_weights(self):
        return super().init_weights()

    def get_transforms(self):
        return super().get_transforms(image_size=self.image_size)

    def get_image_encoder(self):
        return self.vision_model

    def get_text_encoder(self):
        return self.text_model