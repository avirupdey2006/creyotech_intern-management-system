from app.core.encryption import crypto_engine


def test_binary_pdf_encryption_and_sha256_checksum():
    sample_pdf = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    checksum = crypto_engine.sha256_checksum(sample_pdf)
    assert len(checksum) == 64

    encrypted_blob = crypto_engine.encrypt_bytes(sample_pdf)
    assert not encrypted_blob.startswith(b"%PDF")
    assert sample_pdf not in encrypted_blob

    decrypted_blob = crypto_engine.decrypt_bytes(encrypted_blob)
    assert decrypted_blob == sample_pdf
    assert crypto_engine.sha256_checksum(decrypted_blob) == checksum


def test_short_lived_signed_url_verification_and_tamper_rejection():
    doc_id = "d9b2d63d-a233-4123-847a-768389241234"
    sig, expires_at = crypto_engine.generate_signed_url_token(doc_id, expires_in=120)
    assert crypto_engine.verify_signed_url_token(doc_id, expires_at, sig) is True

    # Tampered signature or document ID must fail
    assert crypto_engine.verify_signed_url_token(doc_id, expires_at, sig + "00") is False
    assert crypto_engine.verify_signed_url_token("00000000-0000-0000-0000-000000000000", expires_at, sig) is False

    # Expired URL token must fail
    exp_sig, past_exp = crypto_engine.generate_signed_url_token(doc_id, expires_in=-5)
    assert crypto_engine.verify_signed_url_token(doc_id, past_exp, exp_sig) is False