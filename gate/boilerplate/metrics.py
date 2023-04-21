import torch
import torch.nn.functional as F


def accuracy_top_k(
    logits: torch.Tensor, labels: torch.Tensor, k: int
) -> torch.Tensor:
    """
    Computes the top-k accuracy for a given set of logits and labels.

    Args:
        logits: A tensor of shape (batch_size, num_classes) containing the predicted logits
            for each example in the batch.
        labels: A tensor of shape (batch_size,) containing the ground truth labels
            for each example in the batch.
        k: The value of k for the top-k accuracy calculation.

    Returns:
        A tensor of shape (k,) containing the top-k accuracy for each value of k.
    """
    with torch.no_grad():
        # Get the top-k predictions for each example in the batch
        topk_values, topk_indices = logits.topk(k, dim=1)

        # Convert the ground truth labels to one-hot format
        labels_one_hot = F.one_hot(labels, num_classes=logits.shape[1])

        # Compute the number of correct predictions in the top-k predictions
        correct_topk = (labels_one_hot[topk_indices] == 1).sum(dim=1)

        # Compute the top-k accuracy for each value of k
        top_k_accuracy = correct_topk.float().mean(dim=0)

        return top_k_accuracy * 100.0