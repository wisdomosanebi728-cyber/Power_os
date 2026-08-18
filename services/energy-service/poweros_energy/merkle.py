import hashlib
import json
from typing import List, Tuple, Dict, Any, Optional
from poweros_common.schemas.settlement import MerkleProofItem, MerkleProofSchema


def sha256_hash(data: str) -> str:
    """Computes SHA-256 hash formatted as 0x-prefixed hex string."""
    return "0x" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_pair(left: str, right: str) -> str:
    """Hashes two hex strings deterministically in lexicographical order."""
    combined = left + right if left <= right else right + left
    return "0x" + hashlib.sha256(combined.encode("utf-8")).hexdigest()


class MerkleTree:
    """
    Standard binary Merkle Tree for microgrid energy billing and telemetry notarization.
    """

    def __init__(self, leaves: List[str]):
        self.raw_leaves = leaves
        self.leaf_hashes = [l if l.startswith("0x") else sha256_hash(l) for l in leaves]
        self.layers: List[List[str]] = []
        self._build_tree()

    def _build_tree(self):
        if not self.leaf_hashes:
            self.root = "0x" + "0" * 64
            self.layers = [[]]
            return

        current_layer = list(self.leaf_hashes)
        self.layers.append(current_layer)

        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i + 1] if i + 1 < len(current_layer) else left
                parent = hash_pair(left, right)
                next_layer.append(parent)
            current_layer = next_layer
            self.layers.append(current_layer)

        self.root = self.layers[-1][0]

    def get_proof(self, leaf_index: int) -> List[MerkleProofItem]:
        """Generates the audit proof path for a given leaf index."""
        if leaf_index < 0 or leaf_index >= len(self.leaf_hashes):
            raise IndexError("Leaf index out of bounds")

        proof: List[MerkleProofItem] = []
        idx = leaf_index

        for layer in self.layers[:-1]:
            is_right_child = (idx % 2 == 1)
            pair_idx = idx - 1 if is_right_child else idx + 1

            if pair_idx < len(layer):
                pair_hash = layer[pair_idx]
                proof.append(MerkleProofItem(
                    position="left" if is_right_child else "right",
                    data=pair_hash
                ))
            else:
                # Odd node duplicated
                proof.append(MerkleProofItem(
                    position="right",
                    data=layer[idx]
                ))
            idx = idx // 2

        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: List[MerkleProofItem], root_hash: str) -> bool:
        """Cryptographically verifies a Merkle proof path against the root."""
        current = leaf_hash
        for item in proof:
            if item.position == "left":
                current = hash_pair(item.data, current)
            else:
                current = hash_pair(current, item.data)
        return current.lower() == root_hash.lower()
