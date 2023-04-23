from collections import defaultdict
import json
import sys
from typing import Any, Dict, Optional
from torch.utils.data import Dataset
from torch.utils.data.dataloader import default_collate

from gate.boilerplate.decorators import configurable


class CustomConcatDataset(Dataset):
    """
    A custom PyTorch Dataset class that concatenates multiple datasets.
    📚 Useful for combining data from different sources while maintaining
    the Dataset interface.
    """

    def __init__(self, datasets):
        """
        Constructor for the CustomConcatDataset class.

        :param datasets: A list of PyTorch Dataset objects to concatenate.
        """
        self.datasets = datasets

    def __len__(self):
        """
        Calculate the total length of the concatenated datasets.
        🔢 Returns the sum of the lengths of all individual datasets.

        :return: The total length of the concatenated datasets.
        """
        return sum(len(d) for d in self.datasets)

    def __getitem__(self, idx):
        """
        Get an item from the concatenated datasets based on the provided index.
        🔍 It finds the correct dataset and the corresponding index in that
        dataset.

        :param idx: The index of the desired item in the concatenated datasets.
        :return: The item corresponding to the given index.
        """
        dataset_idx = idx % len(self.datasets)
        item_idx = idx // len(self.datasets)
        return self.datasets[dataset_idx][item_idx]


def dict_to_summary(batch: Dict):
    summary_dict = defaultdict(list)

    if not isinstance(batch, dict) and not isinstance(batch, list):
        batch = [batch.__dict__]

    if isinstance(batch, dict):
        batch = [batch]

    for item in batch:
        for key, value in item.items():
            # print(value)
            if hasattr(value, "shape"):
                summary_dict[key].append((str(value.shape), str(value.dtype)))
            elif hasattr(value, "__len__"):
                summary_dict[key].append(len(value))
            elif value is None:
                summary_dict[key].append(None)
            else:
                summary_dict[key].append(value)

    return summary_dict


def dataclass_collate(batch):
    """Collate data from a list of dataclass objects.

    Args:
        batch (list): List of dataclass objects.

    Returns:
        dict: Dictionary of values from the dataclass objects.
    """
    batch = list(filter(lambda x: x is not None, batch))
    batch = list(filter(lambda x: len(list(x.keys())) != 0, batch))

    try:
        if isinstance(batch[0], dict) or not hasattr(
            batch[0], "__dataclass_fields__"
        ):
            batch = default_collate(batch)
            batch = {key: batch[key][0] for key in batch.keys()}
            return batch
        else:
            batched_dict = {
                key: default_collate(
                    [getattr(sample, key) for sample in batch]
                )
                if getattr(batch[0], key) is not None
                else None
                for key in batch[0].__dict__.keys()
            }
            batched_dict = {key: batched_dict[key][0] for key in batched_dict}
            return batch[0].__class__(**batched_dict)
    except Exception as e:
        print(
            f"Current batch we botched up on "
            f"{json.dumps(dict_to_summary(batch), indent=4)}"
        )
        raise e


@configurable
class GATEDataset(Dataset):
    """
    The GATEDataset class is a wrapper around another dataset, allowing for key
    remapping and applying a task to the data items.

    📚 Attributes:
        - dataset: The input dataset to wrap around
        - task: An optional task to apply to the data items
        - key_remapper_dict: An optional dictionary for key remapping
    """

    def __init__(
        self,
        dataset: Any,
        infinite_sampling: bool = False,
        task: Optional[Any] = None,
        key_remapper_dict: Optional[Dict] = None,
        transforms: Optional[Any] = None,
    ):
        super().__init__()
        self.dataset = dataset
        self.task = task
        self.key_remapper_dict = key_remapper_dict
        self.infinite_sampling = infinite_sampling
        self.transforms = transforms

    def remap_keys(self, item: Dict) -> Dict:
        class_type = None
        if self.key_remapper_dict is not None:
            if isinstance(item, Dict) or hasattr(item, "__dict__"):
                if hasattr(item, "__dict__"):
                    class_type = item.__class__
                    item = item.__dict__

                # 🔄 Remap keys based on the key_remapper_dict
                for key, value in self.key_remapper_dict.items():
                    if key in item:
                        item[value] = item[key]
                        del item[key]

                if class_type is not None:
                    item = class_type(**item)
        return item

    def __len__(self) -> int:
        if self.infinite_sampling:
            return sys.maxsize
        return len(self.dataset)

    def __getitem__(self, index) -> Any:
        if self.infinite_sampling:
            index = index % len(self.dataset)

        item = self.dataset[index]

        item = self.transforms(item) if self.transforms is not None else item

        item: Any = self.remap_keys(item)

        # Apply the task to the item if it exists
        return self.task(item) if self.task is not None else item