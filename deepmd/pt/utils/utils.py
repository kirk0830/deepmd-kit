# SPDX-License-Identifier: LGPL-3.0-or-later
from typing import (
    Optional,
    overload,
)

import ml_dtypes
import numpy as np
import torch
import torch.nn.functional as F

from deepmd.dpmodel.common import PRECISION_DICT as NP_PRECISION_DICT

from .env import (
    DEVICE,
)
from .env import PRECISION_DICT as PT_PRECISION_DICT


class ActivationFn(torch.nn.Module):
    def __init__(self, activation: Optional[str]):
        super().__init__()
        self.activation: str = activation if activation is not None else "linear"

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns the tensor after applying activation function corresponding to `activation`."""
        # See jit supported types: https://pytorch.org/docs/stable/jit_language_reference.html#supported-type

        if self.activation.lower() == "relu":
            return F.relu(x)
        elif self.activation.lower() == "gelu" or self.activation.lower() == "gelu_tf":
            return F.gelu(x, approximate="tanh")
        elif self.activation.lower() == "tanh":
            return torch.tanh(x)
        elif self.activation.lower() == "relu6":
            return F.relu6(x)
        elif self.activation.lower() == "softplus":
            return F.softplus(x)
        elif self.activation.lower() == "sigmoid":
            return torch.sigmoid(x)
        elif self.activation.lower() == "linear" or self.activation.lower() == "none":
            return x
        else:
            raise RuntimeError(f"activation function {self.activation} not supported")


@overload
def to_numpy_array(xx: torch.Tensor) -> np.ndarray: ...


@overload
def to_numpy_array(xx: None) -> None: ...


def to_numpy_array(
    xx,
):
    if xx is None:
        return None
    assert xx is not None
    # Create a reverse mapping of PT_PRECISION_DICT
    reverse_precision_dict = {v: k for k, v in PT_PRECISION_DICT.items()}
    # Use the reverse mapping to find keys with the desired value
    prec = reverse_precision_dict.get(xx.dtype, None)
    prec = NP_PRECISION_DICT.get(prec, None)
    if prec is None:
        raise ValueError(f"unknown precision {xx.dtype}")
    if xx.dtype == torch.bfloat16:
        # https://github.com/pytorch/pytorch/issues/109873
        xx = xx.float()
    return xx.detach().cpu().numpy().astype(prec)


@overload
def to_torch_tensor(xx: np.ndarray) -> torch.Tensor: ...


@overload
def to_torch_tensor(xx: None) -> None: ...


def to_torch_tensor(
    xx,
):
    if xx is None:
        return None
    assert xx is not None
    # Create a reverse mapping of NP_PRECISION_DICT
    reverse_precision_dict = {v: k for k, v in NP_PRECISION_DICT.items()}
    # Use the reverse mapping to find keys with the desired value
    prec = reverse_precision_dict.get(xx.dtype.type, None)
    prec = PT_PRECISION_DICT.get(prec, None)
    if prec is None:
        raise ValueError(f"unknown precision {xx.dtype}")
    if xx.dtype == ml_dtypes.bfloat16:
        # https://github.com/pytorch/pytorch/issues/109873
        xx = xx.astype(np.float32)
    return torch.tensor(xx, dtype=prec, device=DEVICE)


def dict_to_device(sample_dict):
    for key in sample_dict:
        if isinstance(sample_dict[key], list):
            sample_dict[key] = [item.to(DEVICE) for item in sample_dict[key]]
        if isinstance(sample_dict[key], np.float32):
            sample_dict[key] = (
                torch.ones(1, dtype=torch.float32, device=DEVICE) * sample_dict[key]
            )
        else:
            if sample_dict[key] is not None:
                sample_dict[key] = sample_dict[key].to(DEVICE)