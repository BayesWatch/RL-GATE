import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


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
    image_text: Optional[List[SourceModalityConfig]] = None
    text_image: Optional[List[SourceModalityConfig]] = None
    audio_text: Optional[List[SourceModalityConfig]] = None
    text_audio: Optional[List[SourceModalityConfig]] = None
    audio_image: Optional[List[SourceModalityConfig]] = None
    image_audio: Optional[List[SourceModalityConfig]] = None
    video_text: Optional[List[SourceModalityConfig]] = None
    text_video: Optional[List[SourceModalityConfig]] = None
    video_audio: Optional[List[SourceModalityConfig]] = None
    audio_video: Optional[List[SourceModalityConfig]] = None


class GATEModel(nn.Module):
    """🚪 GATEModel class for handling different input and output modalities."""

    def __init__(
        self,
        config: Any,
        model: nn.Module,
        meta_data: Optional[Dict] = None,
    ):
        """
        🏗️ Initialize the GATEModel with a configuration and a base model.

        :param config: TargetModalityConfig object for setting up
        the transformations.
        :param model: Base model to be used for the actual processing.
        """
        super(GATEModel, self).__init__()
        self.model = model
        self.config = config
        self._meta_data = meta_data

        self.supported_input_modalities = {}
        for (
            target_modality_name,
            source_modality_dict_list,
        ) in (
            self.config.__dict__.items()
            if isinstance(self.config, TargetModalityConfig)
            else self.config.items()
        ):
            if source_modality_dict_list is not None:
                for source_modality_dict in source_modality_dict_list:
                    supported_modalities = tuple(
                        key
                        for key, value in (
                            source_modality_dict.__dict__.items()
                            if isinstance(
                                source_modality_dict, SourceModalityConfig
                            )
                            else source_modality_dict.items()
                        )
                        if value is True
                    )
                    self.supported_input_modalities[
                        (supported_modalities, target_modality_name)
                    ] = True

    def parameters(self, recurse: bool = True) -> Iterator[torch.nn.Parameter]:
        return self.model.parameters(recurse)

    def named_parameters(
        self, prefix: str = "", recurse: bool = True
    ) -> Iterator[Tuple[str, torch.nn.Parameter]]:
        return self.model.named_parameters(prefix, recurse)

    @property
    def meta_data(self) -> Optional[dict]:
        return self._meta_data

    @meta_data.setter
    def meta_data(self, meta_data: dict) -> None:
        self._meta_data = meta_data

        if meta_data is None:
            return

        for key, value in meta_data.items():
            if hasattr(self.model, key):
                setattr(self.model, key, value)

    def process_modalities(
        self,
        target_modality_name: str,
        input_modalities: Dict[str, Any],
        extra_arg_items: Dict[str, Any] = None,
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

        if key in self.supported_input_modalities:
            if extra_arg_items is not None:
                input_modalities.update(extra_arg_items)

            return self.model(**input_modalities)
        else:
            raise ValueError(f"Unsupported modality: {key}")

    def get_valid_combinations(self) -> List[Tuple[Tuple[str, ...], str]]:
        """
        📋 Get the list of valid input and target modality combinations.

        :return: A list of tuples containing input modalities and target
        modality names.
        """
        return list(self.supported_input_modalities.keys())

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
        non_data_related_items = {
            key: value
            for key, value in input_dict.items()
            if key not in self.supported_input_modalities
        }

        for (
            supported_modalities,
            target_modality_name,
        ) in self.get_valid_combinations():
            model_inputs = {
                modality: input_dict[modality]
                for modality in supported_modalities
            }

            # 📞 Call the process_modalities method with the
            # target_modality_name and input_modalities

            try:
                output = self.process_modalities(
                    target_modality_name=target_modality_name,
                    input_modalities=model_inputs,
                    extra_arg_items=non_data_related_items,
                )
                # 💾 Store the output in the output_dict
                if target_modality_name not in output_dict:
                    output_dict[target_modality_name] = {}
                output_dict[target_modality_name][
                    "_".join(supported_modalities)
                ] = output
            except NotImplementedError:
                logger.warning(
                    f"Ignoring processing modality pair: target: {target_modality_name}, supported_ {supported_modalities}"
                )
                pass  # 🛑 Handle unsupported cases, or do nothing
                # if no action is needed for unsupported cases

        return output_dict


def simple_init(input_module: nn.Module):
    for name, module in input_module.named_modules():
        if isinstance(module, torch.nn.Linear):
            torch.nn.init.normal_(module.weight, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, torch.nn.Embedding):
            torch.nn.init.normal_(module.weight, std=0.02)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()
        elif isinstance(module, torch.nn.LayerNorm):
            torch.nn.init.ones_(module.weight)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, torch.nn.Conv2d):
            torch.nn.init.normal_(module.weight, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, torch.nn.Conv1d):
            torch.nn.init.normal_(module.weight, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, torch.nn.ConvTranspose1d):
            torch.nn.init.normal_(module.weight, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)


def recursive_mean(tensor_dict):
    if isinstance(tensor_dict, dict):
        return {k: recursive_mean(v) for k, v in tensor_dict.items()}
    elif isinstance(tensor_dict, list):
        if all(isinstance(i, torch.Tensor) for i in tensor_dict):
            return torch.mean(torch.stack(tensor_dict), dim=0)
        elif all(isinstance(i, dict) for i in tensor_dict):
            keys = tensor_dict[0].keys()
            return {
                key: recursive_mean([d[key] for d in tensor_dict])
                for key in keys
            }
        else:
            return [recursive_mean(i) for i in tensor_dict]
    elif isinstance(tensor_dict, torch.Tensor):
        return tensor_dict
    elif isinstance(tensor_dict, bool):
        return tensor_dict
    else:
        raise ValueError(
            f"Unsupported data type for recursive_mean, data type is {type(tensor_dict)}"
        )


def flatten_dict(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def print_dict_structure(d, indent=0):
    from rich import print

    for key, value in d.items():
        logger.info(" " * indent + str(key))
        if isinstance(value, dict):
            print_dict_structure(value, indent + 2)


class Ensemble(nn.Module):
    """
    This class represents an ensemble of PyTorch models. It can compute ensemble predictions,
    weighted ensemble predictions, and predictions from a "model soup" that averages the models' parameters.
    """

    def __init__(self, models: list[nn.Module]):
        """
        Initialize the Ensemble with a list of models and optional weights.

        Args:
            models (list[nn.Module]): A list of PyTorch models.
            weights (list[float], optional): A list of weights for the models. Defaults to None, which gives equal weight to all models.
        """
        super(Ensemble, self).__init__()
        self.models = nn.ModuleList(models)
        self.compute_loss_and_metrics = None
        self.iou_metrics_dict = None

        for model in self.models:
            model.eval()

        for name in dir(self.models[0]):
            member = getattr(self.models[0], name)
            if hasattr(member, "__used_in_ensemble__"):
                setattr(self, name, member)

        if self.iou_metrics_dict is not None:
            for value in self.iou_metrics_dict.values():
                value.reset()

        logger.info(f"Ensemble model with {len(self.models)} models created.")

    def forward(self, *args, **kwargs) -> dict[str, torch.Tensor]:
        """
        Compute the ensemble predictions, weighted ensemble predictions, and model soup predictions.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict[str, torch.Tensor]: A dictionary containing the ensemble predictions, weighted ensemble predictions, and model soup predictions.
        """

        with torch.inference_mode():
            # # Get the outputs from each model

            model_outputs = [model(*args, **kwargs) for model in self.models]
            labels = None

            if isinstance(model_outputs[0], torch.Tensor):
                logits = model_outputs
            else:
                logits = [output["logits"] for output in model_outputs]

            if "labels" in kwargs:
                labels = kwargs["labels"]

            if not isinstance(model_outputs[0], torch.Tensor):
                if "labels" in model_outputs[0]:
                    labels = model_outputs[0]["labels"]

            ensemble_pred = {}

            if isinstance(logits[0], torch.Tensor):
                ensemble_pred = torch.mean(
                    torch.stack(logits),
                    dim=0,
                )
            else:
                for key in logits[0].keys():
                    ensemble_pred[key] = recursive_mean(
                        [output[key] for output in logits]
                    )

            output_dict = {"logits": ensemble_pred}

            if (
                labels is not None
                and self.compute_loss_and_metrics is not None
            ):
                metrics = self.compute_loss_and_metrics(
                    logits=ensemble_pred, labels=labels
                )
                output_dict.update(metrics)

            outputs = flatten_dict(output_dict)

            return outputs
