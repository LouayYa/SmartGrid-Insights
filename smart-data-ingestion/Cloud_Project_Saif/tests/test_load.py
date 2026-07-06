API_PREFIX = "/api/v1"

VALID_CSV = """Date,Time,Global_active_power,Global_reactive_power,Voltage,Global_intensity,Sub_metering_1,Sub_metering_2,Sub_metering_3
1/1/07,00:00:00,1.234,0.100,240.10,5.0,0.0,1.0,17.0
1/1/07,00:01:00,?,0.100,240.20,5.1,0.0,1.0,17.0
30/6/2007,23:59:00,2.500,0.200,239.80,10.0,1.0,0.0,18.0
"""

MISSING_COLUMN_CSV = """Date,Time,Global_active_power
1/1/07,00:00:00,1.234
"""


def test_load_dataset(client, tmp_path):
    csv_file = tmp_path / "consumption.csv"
    csv_file.write_text(VALID_CSV)

    response = client.post(f"{API_PREFIX}/load", params={"csv_path": str(csv_file)})

    assert response.status_code == 201
    body = response.json()
    assert body == {"records_loaded": 3, "status": "success"}

    listed = client.get(f"{API_PREFIX}/consumption").json()
    assert len(listed) == 3
    # The "?" missing value should have been coerced to NULL, not dropped.
    assert any(row["Global_active_power"] is None for row in listed)


def test_load_dataset_is_idempotent(client, tmp_path):
    csv_file = tmp_path / "consumption.csv"
    csv_file.write_text(VALID_CSV)

    client.post(f"{API_PREFIX}/load", params={"csv_path": str(csv_file)})
    response = client.post(f"{API_PREFIX}/load", params={"csv_path": str(csv_file)})

    assert response.status_code == 201
    assert response.json()["records_loaded"] == 3

    listed = client.get(f"{API_PREFIX}/consumption").json()
    assert len(listed) == 3


def test_load_dataset_missing_file(client, tmp_path):
    missing_path = tmp_path / "does-not-exist.csv"

    response = client.post(f"{API_PREFIX}/load", params={"csv_path": str(missing_path)})

    assert response.status_code == 404


def test_load_dataset_missing_columns(client, tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text(MISSING_COLUMN_CSV)

    response = client.post(f"{API_PREFIX}/load", params={"csv_path": str(csv_file)})

    assert response.status_code == 400
