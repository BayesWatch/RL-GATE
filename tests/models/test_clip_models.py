import torch
import torch.nn.functional as F

from gate.models.clip import ModelAndTransform, build_model
from gate.models.core import (
    GATEModel,
    SourceModalityConfig,
    TargetModalityConfig,
)


def test_build_model():
    model_and_transform = build_model()

    assert isinstance(model_and_transform, ModelAndTransform)
    assert model_and_transform.model is not None
    assert model_and_transform.transform is not None


def test_clip_with_linear_forward():
    model_and_transform = build_model()

    x_dummy = torch.rand(2, 3, 224, 224)
    y_dummy = torch.randint(0, 100, (2,))

    model = model_and_transform.model
    transform = model_and_transform.transform

    input_images = torch.cat(
        [
            transform({"image": x, "labels": y})["input_images"]
            for x, y in zip(x_dummy, y_dummy)
        ],
        dim=0,
    )

    output = model.forward({"pixel_values": input_images})

    assert output.shape == (2, 100)

    loss = F.cross_entropy(output, y_dummy)
    assert loss.item() > 0


def test_clip_with_linear_forward():
    model_and_transform = build_model()
    model = model_and_transform.model
    transform = model_and_transform.transform

    source_config1 = SourceModalityConfig(image=True)

    target_config = TargetModalityConfig(image=[source_config1])

    x_dummy = torch.rand(2, 3, 224, 224)
    y_dummy = torch.randint(0, 100, (2,))

    model = model_and_transform.model
    transform = model_and_transform.transform

    model = GATEModel(
        target_config, model, key_remapper_dict={"image": "pixel_values"}
    )

    input_images = torch.cat(
        [
            transform({"image": x, "labels": y})["pixel_values"]
            for x, y in zip(x_dummy, y_dummy)
        ],
        dim=0,
    )

    output = model.forward({"image": input_images})
    assert output["image"]["image"].shape == (2, 100)

    loss = F.cross_entropy(output["image"]["image"], y_dummy)
    assert loss.item() > 0