import io
import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from unittest.mock import patch

import pandas as pd

import main
from server import DashboardHandler, app
from src.hotspot_detection import detect_hotspots
from src.preprocessing import prepare
import src.visualization as visualization
from src.visualization import _measurement_columns, save_pm25_trend


class DynamicDatasetTests(unittest.TestCase):
    def test_haversine_speed_and_ambiguous_or_missing_locations(self):
        source = pd.DataFrame({
            "timestamp": [
                "2025-01-01 00:00:00", "2025-01-01 01:00:00",
                "2025-01-01 02:00:00", "2025-01-01 02:00:00",
                "2025-01-01 03:00:00", "2025-01-01 04:00:00",
                "2025-01-01 05:00:00", "2025-01-01 06:00:00",
            ],
            "latitude": [0, 0, 0, 0, 0, None, 0, 0],
            "longitude": [0, 1, 2, 3, 4, 5, 6, 6],
            "PM2.5": [1, 2, 3, 4, 5, 6, 7, 8],
        })
        speeds = prepare(source, "track.csv")["estimated_speed_kmh"]
        self.assertAlmostEqual(speeds.iloc[1], 111.195, places=2)
        self.assertTrue(speeds.iloc[[0, 2, 3, 4, 5, 6]].isna().all())
        self.assertEqual(speeds.iloc[7], 0)

    def test_hotspot_speed_correlation_and_insufficient_variation(self):
        source = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=4, freq="s"),
            "latitude": [0, 0, 0, 0],
            "longitude": [0, 0.000001, 0.000003, 0.000006],
            "PM2.5": [0, 1, 2, 3],
        })
        cleaned = prepare(source, "track.csv")
        hotspot = detect_hotspots(cleaned, min_readings=1).iloc[0]
        self.assertEqual(hotspot["speed_pm25_pairs"], 3)
        self.assertAlmostEqual(hotspot["speed_pm25_correlation"], 1)
        self.assertAlmostEqual(
            hotspot["average_speed_kmh"], cleaned["estimated_speed_kmh"].mean()
        )
        cleaned["PM2.5"] = 1
        self.assertTrue(pd.isna(
            detect_hotspots(cleaned, min_readings=1).iloc[0]["speed_pm25_correlation"]
        ))
        cleaned.loc[2:, "estimated_speed_kmh"] = float("nan")
        self.assertTrue(pd.isna(
            detect_hotspots(cleaned, min_readings=1).iloc[0]["speed_pm25_correlation"]
        ))

    def test_prepares_and_plots_dataset_with_unfamiliar_measurement_columns(self):
        source = pd.DataFrame({
            "When recorded": ["2025-01-01 10:00", "2025-01-01 11:00"],
            "NO2 level": ["12.5", "17.5"],
            "Latitude": [21.1, 21.2],
            "station_id": [1, 2],
        })

        prepared = prepare(source, "custom.csv")
        self.assertEqual(prepared["timestamp"].dt.date.nunique(), 1)
        self.assertTrue(prepared["PM2.5"].isna().all())
        self.assertIn("NO2 level", _measurement_columns(prepared))

        with tempfile.TemporaryDirectory() as output:
            with patch("src.visualization.FIGURES", Path(output)):
                save_pm25_trend(prepared)
            chart = Path(output) / "daily_pm25_trend.png"
            self.assertTrue(chart.is_file())
            self.assertGreater(chart.stat().st_size, 0)

    def test_prefers_pm25_when_available(self):
        df = pd.DataFrame({
            "PM2.5": [10, 20],
            "NO2": [100, 200],
        })

        self.assertEqual(list(_measurement_columns(df)), ["PM2.5"])

    def test_pipeline_runs_without_pm25_measurements(self):
        prepared = prepare(pd.DataFrame({
            "When recorded": ["2025-01-01 10:00", "2025-01-01 11:00"],
            "NO2 level": [12.5, 17.5],
        }), "custom.csv")

        with tempfile.TemporaryDirectory() as output:
            output_path = Path(output)
            with patch.object(main, "OUT", output_path):
                with patch.object(main, "run_preprocessing", return_value=prepared):
                    with patch.object(
                        visualization, "FIGURES", output_path / "figures"
                    ):
                        main.main()

            self.assertTrue((output_path / "daily_pollution_summary.csv").is_file())
            self.assertTrue(
                (output_path / "figures" / "daily_pm25_trend.png").is_file()
            )

    def test_prepare_without_date_keeps_and_deduplicates_rows(self):
        source = pd.DataFrame({
            "sensor": ["A", "A", "B"],
            "fine particles": [12, 12, 25],
            "north": [21, 21, 91],
            "east": [72, 72, 73],
        })
        cleaned = prepare(source, "city.csv", {
            "PM2.5": "fine particles", "latitude": "north", "longitude": "east",
        }, allow_missing_timestamp=True)
        self.assertEqual(len(cleaned), 2)
        self.assertTrue(cleaned["timestamp"].isna().all())
        self.assertEqual(cleaned["PM2.5"].tolist(), [12, 25])
        self.assertTrue(pd.isna(cleaned.iloc[1]["latitude"]))

    def test_prepare_maps_date_and_time_and_preserves_mapped_sources(self):
        source = pd.DataFrame({
            "observed": ["2025-01-02", "invalid"],
            "clock": ["10:30:00", "11:00:00"],
            "latitude": [22.5, 23.0],
            "longitude": [88.3, 89.0],
        })
        cleaned = prepare(source, "city.csv", {
            "timestamp": "observed", "time": "clock",
            "latitude": "longitude", "longitude": "latitude",
        }, allow_missing_timestamp=True)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(str(cleaned.iloc[0]["timestamp"]), "2025-01-02 10:30:00")
        self.assertEqual(cleaned.iloc[0]["latitude"], 88.3)
        self.assertEqual(cleaned.iloc[0]["longitude"], 22.5)


class UploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def upload(self, name, content, mapping=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        request_headers = {"X-File-Name": name}
        request_headers.update(headers or {})
        try:
            connection.request(
                "POST", "/api/upload?" + urlencode(mapping or {}),
                body=content, headers=request_headers,
            )
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_csv_upload_maps_columns_and_returns_isolated_analysis(self):
        source = "observed,reading,north,east\n" + "".join(
            f"2025-01-{day:02d},{day},22.5,88.3\n" for day in range(1, 12)
        )
        status, result = self.upload("city.csv", source.encode(), {
            "timestamp": "observed", "PM2.5": "reading",
            "latitude": "north", "longitude": "east",
        })
        self.assertEqual(status, 200)
        self.assertEqual(result["input_rows"], 11)
        self.assertEqual(result["output_rows"], 11)
        self.assertEqual(result["priority"][0]["readings"], 11)
        self.assertEqual(result["priority"][0]["latitude_group"], 22.5)
        downloaded = pd.read_csv(io.StringIO(result["cleaned_csv"]))
        self.assertEqual(downloaded["PM2.5"].tolist(), list(range(1, 12)))

    def test_upload_exposes_speed_and_local_correlation(self):
        source = "timestamp,latitude,longitude,PM2.5\n" + "".join(
            f"2025-01-01 00:00:{i:02d},0,{i * (i + 1) * 0.00000005},{i}\n"
            for i in range(11)
        )
        status, result = self.upload("track.csv", source.encode())
        self.assertEqual(status, 200)
        self.assertIsNone(result["cleaned"][0]["estimated_speed_kmh"])
        self.assertGreater(result["cleaned"][1]["estimated_speed_kmh"], 0)
        self.assertEqual(result["priority"][0]["speed_pm25_pairs"], 10)
        self.assertAlmostEqual(result["priority"][0]["speed_pm25_correlation"], 1)
        self.assertEqual(result["priority"][0]["ips"], 100)

    def test_upload_averages_each_pollutant_at_hotspots(self):
        source = "timestamp,latitude,longitude,PM2.5,pm10,co2,so2,no2,co,o3,h2s\n"
        source += "".join(
            f"2025-01-{i:02d},22.5,88.3,20,10,20,30,40,50,60,70\n"
            for i in range(1, 11)
        )
        source += "2025-01-11,22.5,88.3,,21,31,invalid,51,61,71,81\n"
        status, result = self.upload("pollutants.csv", source.encode())
        self.assertEqual(status, 200)
        hotspot = result["priority"][0]
        self.assertEqual(hotspot["readings"], 10)
        for field, expected in {
            "average_pm10": 11, "average_co2": 21, "average_so2": 30,
            "average_no2": 41, "average_co": 51, "average_o3": 61,
            "average_h2s": 71,
        }.items():
            with self.subTest(field=field):
                self.assertAlmostEqual(hotspot[field], expected)
        self.assertEqual(hotspot["ips"], 100)

    def test_missing_pollutants_are_not_zero_filled(self):
        source = "timestamp,latitude,longitude,PM2.5\n" + "".join(
            f"2025-01-{i:02d},22.5,88.3,20\n" for i in range(1, 11)
        )
        status, result = self.upload("pollutants.csv", source.encode())
        self.assertEqual(status, 200)
        self.assertIsNone(result["priority"][0]["average_co2"])

    def test_csv_upload_skips_rows_with_extra_fields_and_reports_count(self):
        headers = ["timestamp", "PM2.5", "latitude", "longitude"] + [
            f"extra_{index}" for index in range(11)
        ]
        valid = lambda date: [date, "12", "22.5", "88.3"] + ["x"] * 11
        malformed = ["2025-01-02", "12", "22.5", "88.3"] + ["x"] * 14
        content = ",".join(headers) + "\n"
        content += ",".join(valid("2025-01-01")) + "\n"
        content += ",".join(malformed) + "\n"
        content += ",".join(valid("2025-01-03")) + "\n"

        status, result = self.upload("city.csv", content.encode())
        self.assertEqual(status, 200)
        self.assertEqual(result["input_rows"], 3)
        self.assertEqual(result["output_rows"], 2)
        self.assertEqual(result["skipped_malformed_rows"], 1)

    def test_excel_without_date_and_invalid_mapping(self):
        content = io.BytesIO()
        pd.DataFrame({"value": [1, 1, 2]}).to_excel(content, index=False)
        status, result = self.upload("city.xlsx", content.getvalue())
        self.assertEqual(status, 200)
        self.assertFalse(result["has_timestamp"])
        self.assertEqual(result["output_rows"], 2)
        self.assertEqual(result["priority"], [])
        status, result = self.upload("city.xlsx", content.getvalue(), {"PM2.5": "missing"})
        self.assertEqual(status, 400)
        self.assertIn("Invalid column mapping", result["error"])

    def test_rejects_bad_inputs(self):
        for name, content in [("city.txt", b"data"), ("city.csv", b""), ("city.csv", b'a,b\n"bad')]:
            with self.subTest(name=name, content=content):
                status, result = self.upload(name, content)
                self.assertEqual(status, 400)
                self.assertTrue(result["error"])

    def test_flask_app_serves_dashboard_and_processes_uploads(self):
        client = app.test_client()
        dashboard = client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        dashboard.close()
        script = client.get("/script.js")
        self.assertEqual(script.status_code, 200)
        script.close()

        source = "observed,reading,north,east\n" + "".join(
            f"2025-01-{day:02d},{day},22.5,88.3\n" for day in range(1, 12)
        )
        response = client.post(
            "/api/upload?timestamp=observed&PM2.5=reading&latitude=north&longitude=east",
            data=source.encode(),
            headers={"X-File-Name": "city.csv"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["output_rows"], 11)

        response = client.post(
            "/api/upload",
            data=b"timestamp,PM2.5\n2025-01-01,10\n",
            headers={
                "X-File-Name": "city.csv",
                "Origin": "https://other.example",
            },
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
