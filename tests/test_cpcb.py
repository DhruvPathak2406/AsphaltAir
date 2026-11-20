import io
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from server import DashboardHandler, app
from src.cpcb import CPCBError, get_station_data


def record(pollutant, value, timestamp="19-11-2026 22:00:00", station="Station A"):
    return {
        "station": station, "latitude": "21.17", "longitude": "72.83",
        "last_update": timestamp, "pollutant_id": pollutant, "avg_value": value,
    }


class CPCBTests(unittest.TestCase):
    def test_paginates_and_uses_latest_value_per_pollutant(self):
        pages = [
            {"total": 5, "records": [
                record("PM2.5", "10", "19-11-2026 21:00:00"),
                record("OZONE", "NA"),
            ]},
            {"total": 5, "records": [
                record("PM2.5", "25"),
                record("OZONE", "12"),
                record("PM10", "9", "bad time"),
            ]},
        ]
        urls = []

        def fetch(request, timeout):
            urls.append(parse_qs(urlparse(request.full_url).query))
            return io.BytesIO(json.dumps(pages.pop(0)).encode())

        with patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": "test-key"}):
            with patch("src.cpcb.urlopen", side_effect=fetch):
                result = get_station_data("Surat", "Gujarat")

        self.assertEqual([url["offset"][0] for url in urls], ["0", "2"])
        self.assertEqual(urls[0]["filters[city]"], ["Surat"])
        station = result["stations"][0]
        self.assertEqual(station["average_pm25"], 25)
        self.assertEqual(station["average_o3"], 12)
        self.assertNotIn("average_pm10", station)
        self.assertEqual(station["source_times"]["average_pm25"], "19-11-2026 22:00:00")
        self.assertEqual(result["skipped_records"], 1)

    def test_incomplete_page_is_an_error(self):
        page = {"total": 2, "records": []}
        with patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": "test-key"}):
            with patch("src.cpcb.urlopen", return_value=io.BytesIO(json.dumps(page).encode())):
                with self.assertRaisesRegex(CPCBError, "incomplete"):
                    get_station_data("Surat")

    def test_upstream_error_does_not_expose_api_key(self):
        error = HTTPError("https://example.test/?api-key=test-key", 403, "Forbidden", {}, None)
        with patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": "test-key"}):
            with patch("src.cpcb.urlopen", side_effect=error):
                with self.assertRaises(CPCBError) as raised:
                    get_station_data("Surat")
        self.assertIn("403", str(raised.exception))
        self.assertNotIn("test-key", str(raised.exception))

    def test_endpoint_reports_missing_key_and_rejects_empty_city(self):
        client = app.test_client()
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(client.get("/api/cpcb?city=Surat").status_code, 503)
            self.assertEqual(client.get("/api/cpcb").status_code, 400)

    def test_endpoint_returns_station_data_without_a_priority_score(self):
        payload = {"city": "Surat", "state": "", "stations": [
            {"station_name": "A", "latitude_group": 21.17, "longitude_group": 72.83,
             "average_pm25": 25, "source_times": {"average_pm25": "19-11-2026 22:00:00"}}
        ], "skipped_records": 0}
        with patch("server.get_station_data", return_value=payload):
            response = app.test_client().get("/api/cpcb?city=Surat")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("ips", response.get_json()["stations"][0])

    def test_local_http_server_serves_cpcb_endpoint(self):
        payload = {"city": "Surat", "state": "", "stations": [], "skipped_records": 0}
        server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch("server.get_station_data", return_value=payload):
                connection = HTTPConnection("127.0.0.1", server.server_port)
                try:
                    connection.request("GET", "/api/cpcb?city=Surat")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read()), payload)
                finally:
                    connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
