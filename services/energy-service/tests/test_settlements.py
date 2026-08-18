import pytest
from datetime import datetime, timezone, timedelta
from poweros_energy.merkle import MerkleTree, sha256_hash
from poweros_energy.settlement_engine import SettlementEngine


def test_merkle_tree_hashing_and_verification():
    leaves = [
        "invoice_data_user_1_amount_10.50",
        "invoice_data_user_2_amount_25.00",
        "invoice_data_user_3_amount_40.20",
        "invoice_data_user_4_amount_12.80",
    ]

    tree = MerkleTree(leaves)
    assert tree.root.startswith("0x")
    assert len(tree.root) == 66  # 0x + 64 hex chars

    # Test audit proof for user 2 (index 1)
    proof = tree.get_proof(1)
    assert len(proof) > 0

    leaf_hash = tree.leaf_hashes[1]
    is_valid = MerkleTree.verify_proof(leaf_hash, proof, tree.root)
    assert is_valid is True

    # Tampering test
    fake_leaf = sha256_hash("tampered_invoice_data")
    is_fake_valid = MerkleTree.verify_proof(fake_leaf, proof, tree.root)
    assert is_fake_valid is False


def test_settlement_engine_epoch_calculation():
    community_id = "00000000-0000-0000-0000-000000000001"
    now = datetime.now(timezone.utc)

    consumer_meters = [
        {"user_id": "usr-01", "user_name": "Clinic", "device_id": "m-01", "consumption_kwh": 100.0},
        {"user_id": "usr-02", "user_name": "Bakery", "device_id": "m-02", "consumption_kwh": 200.0},
    ]

    generation = {
        "solar_kwh": 250.0,
        "battery_kwh": 50.0,
        "grid_kwh": 0.0,
        "generator_kwh": 0.0,
    }

    summary, tree = SettlementEngine.calculate_epoch_settlement(
        community_id=community_id,
        epoch_start=now - timedelta(days=7),
        epoch_end=now,
        consumer_meters=consumer_meters,
        generation_summary=generation,
    )

    assert summary.total_energy_consumed_kwh == 300.0
    assert len(summary.invoices) == 2
    assert summary.merkle_root_hash == tree.root
    assert summary.total_savings > 0.0

    # Verify first invoice proof
    inv0 = summary.invoices[0]
    proof0 = tree.get_proof(0)
    assert MerkleTree.verify_proof(inv0.leaf_hash, proof0, summary.merkle_root_hash) is True
