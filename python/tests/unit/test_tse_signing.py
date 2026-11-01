from python.business.tse_signing import render_process_data


def test_process_data_has_dsfink_vat_order_and_payment():
    assert render_process_data({0.19: 75.33, 0.07: 7.99}, ec_zahlung=False) == (
        "Beleg^75.33_7.99_0.00_0.00_0.00^83.32:Bar"
    )


def test_process_data_training_prefix_and_card_payment():
    assert render_process_data({0.0: 5.0}, ec_zahlung=True, training=True) == (
        "AVTraining^0.00_0.00_0.00_0.00_5.00^5.00:Unbar"
    )
