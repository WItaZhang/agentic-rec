"""SASRec-style causal self-attention architecture; no fitting or data I/O.

Uses full-softmax cross entropy in the trainer, rather than the original
paper's sampled objective. This is an adapted baseline, not a numerical reproduction.
"""

import hashlib
import json
import math

import numpy as np
import torch
from torch import nn


class CausalSequenceModel(nn.Module):
    def __init__(self, item_count, max_length, dimension, heads, layers, dropout,
                 feedforward_multiplier, embedding_std):
        super().__init__()
        self.max_length = max_length
        self.dimension = dimension
        self.items = nn.Embedding(item_count + 1, dimension, padding_idx=0)
        self.positions = nn.Embedding(max_length, dimension)
        self.dropout = nn.Dropout(dropout)
        block = nn.TransformerEncoderLayer(dimension, heads, dim_feedforward=dimension * feedforward_multiplier,
                                           dropout=dropout, activation="gelu", batch_first=True,
                                           norm_first=True)
        self.encoder = nn.TransformerEncoder(block, layers, enable_nested_tensor=False)
        self.normalization = nn.LayerNorm(dimension)
        nn.init.normal_(self.items.weight, std=embedding_std)
        nn.init.normal_(self.positions.weight, std=embedding_std)
        with torch.no_grad():
            self.items.weight[0].zero_()

    def encode(self, tokens):
        length = tokens.shape[1]
        positions = torch.arange(length, device=tokens.device)
        inputs = self.dropout(self.items(tokens) * math.sqrt(self.dimension) + self.positions(positions))
        causal_mask = torch.ones(length, length, dtype=torch.bool, device=tokens.device).triu(1)
        return self.normalization(self.encoder(inputs, mask=causal_mask, src_key_padding_mask=tokens == 0))

    def forward(self, tokens):
        encoded = self.encode(tokens)
        last = (tokens != 0).sum(dim=1) - 1
        representations = encoded[torch.arange(len(tokens), device=tokens.device), last]
        scores = representations @ self.items.weight.T
        return scores.masked_fill(torch.arange(scores.shape[1], device=scores.device)[None, :] == 0, -1e9)


class SequenceRecommender:
    def __init__(self, network, catalog, popularity):
        self.network = network.eval()
        self.catalog = tuple(catalog)
        self.popularity = tuple(popularity)
        self.indices = {item: i + 1 for i, item in enumerate(catalog)}
        value = hashlib.sha256(json.dumps([self.catalog, self.popularity]).encode())
        for name, tensor in sorted(network.state_dict().items()):
            value.update(name.encode())
            value.update(tensor.detach().cpu().numpy().tobytes())
        self.checkpoint_hash = value.hexdigest()

    @property
    def ranked_items(self):
        return self.catalog

    def score_history(self, history, threshold):
        sequence = [self.indices[event.item] for event in history
                    if event.rating >= threshold and event.item in self.indices][-self.network.max_length:]
        if not sequence:
            return np.asarray(self.popularity, dtype=float)
        with torch.inference_mode():
            return self.network(torch.tensor([sequence], dtype=torch.long))[0, 1:].numpy()
