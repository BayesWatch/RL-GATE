from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn


@dataclass
class SourceModalityConfig:
    """📄 Class representing the source modalities configurations."""

    image: bool = False
    text: bool = False
    audio: bool = False
    video: bool = False


@dataclass
class TargetModalityConfig:
    """🎯 Class representing the target modalities configurations."""

    image: Optional[List[SourceModalityConfig]] = None
    text: Optional[List[SourceModalityConfig]] = None
    audio: Optional[List[SourceModalityConfig]] = None
    video: Optional[List[SourceModalityConfig]] = None


class GATEModel(nn.Module):
    """🚪 GATEModel class for handling different input and output modalities."""

    def __init__(self, config: Any, model: nn.Module):
        """
        🏗️ Initialize the GATEModel with a configuration and a base model.

        :param config: TargetModalityConfig object for setting up
        the transformations.
        :param model: Base model to be used for the actual processing.
        """
        super().__init__()
        self.model = model
        self.config = config

        self.supported_transforms = {}
        for (
            target_modality_name,
            source_modality_dict_list,
        ) in self.config.__dict__.items():
            if source_modality_dict_list is not None:
                for source_modality_dict in source_modality_dict_list:
                    supported_modalities = tuple(
                        key
                        for key, value in source_modality_dict.__dict__.items()
                        if value is True
                    )
                    self.supported_transforms[
                        (supported_modalities, target_modality_name)
                    ] = True

    def process_modalities(
        self, target_modality_name: str, **input_modalities: Dict[str, Any]
    ):
        """
        🔄 Process the input modalities and generate the output in the
        specified target modality.

        :param target_modality_name: Target modality name (e.g., 'image',
        'text', 'audio', 'video')
        :param input_modalities: Input modalities as keyword arguments.
        :raises ValueError: If the given transformation is unsupported.
        """
        key = (tuple(input_modalities.keys()), target_modality_name)
        if key in self.supported_transforms:
            # 🎛️ Define the transformation logic here
            raise NotImplementedError
        else:
            raise ValueError(f"Unsupported transformation: {key}")

    def get_valid_combinations(self) -> List[Tuple[Tuple[str, ...], str]]:
        """
        📋 Get the list of valid input and target modality combinations.

        :return: A list of tuples containing input modalities and target
        modality names.
        """
        return list(self.supported_transforms.keys())

    def forward(
        self, input_dict: Dict
    ) -> Dict[str, Dict[Tuple[str, ...], Any]]:
        """
        🚀 Forward pass of the GATEModel.

        :param input_dict: Dictionary of input modalities.
        :return: A nested dictionary with target modalities as outer keys,
                source modalities as inner keys, and the corresponding output
                as the value.
        """
        output_dict = {}

        for (
            supported_modalities,
            target_modality_name,
        ) in self.get_valid_combinations():
            input_modalities = {
                modality: input_dict[modality]
                for modality in supported_modalities
            }
            # 📞 Call the process_modalities method with the
            # target_modality_name and input_modalities
            try:
                output = self.process_modalities(
                    target_modality_name, **input_modalities
                )
                # 💾 Store the output in the output_dict
                if target_modality_name not in output_dict:
                    output_dict[target_modality_name] = {}
                output_dict[target_modality_name][
                    supported_modalities
                ] = output
            except NotImplementedError:
                pass  # 🛑 Handle unsupported cases, or do nothing
                # if no action is needed for unsupported cases

        return output_dict


if __name__ == "__main__":
    from rich import print

    gate_model_config = TargetModalityConfig(
        image=[
            SourceModalityConfig(text=True, image=True),
            SourceModalityConfig(audio=True, image=True),
            SourceModalityConfig(audio=True, text=True, image=True),
        ]
    )

    model = GATEModel(gate_model_config, nn.Linear(10, 10))

    print(model.__dict__)