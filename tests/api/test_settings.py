"""The settings of the printers kept on the server."""

import json

from app.labeldesigner import printer_settings

from tests.helpers import make_client

URL = '/labeldesigner/api/settings'


def test_settings_are_kept_per_printer_and_common(tmp_path):
    client = make_client(tmp_path, empty_repo=True, model='QL-800')
    assert client.get(URL, query_string={'printer': 'tcp://a'}).get_json() == {}
    r = client.post(URL, data={'printer': 'tcp://a', 'label_size': '62', 'cut': 'last', 'quality': 'fast'})
    assert r.status_code == 200
    assert r.get_json()['settings'] == {'label_size': '62', 'cut': 'last', 'quality': 'fast'}
    # Another printer has its own label size and cutting, the quality is
    # the same for all
    assert client.get(URL, query_string={'printer': 'tcp://b'}).get_json() == {'quality': 'fast'}
    # Only what is named changes, another browser's change stays
    client.post(URL, json={'printer': 'tcp://a', 'collate': '0'})
    assert client.get(URL, query_string={'printer': 'tcp://a'}).get_json() == {
        'label_size': '62', 'cut': 'last', 'quality': 'fast', 'collate': '0'}
    # An empty value removes one
    client.post(URL, data={'printer': 'tcp://a', 'label_size': ''})
    assert 'label_size' not in client.get(URL, query_string={'printer': 'tcp://a'}).get_json()
    # The same device however it is written
    assert client.get(URL, query_string={'printer': 'tcp://A:9100'}).get_json()['cut'] == 'last'


def test_printer_status_tells_the_settings(tmp_path):
    client = make_client(tmp_path, empty_repo=True, model='QL-800')
    client.post(URL, data={'printer': 'simulation', 'label_size': '62', 'date_format': '%d.%m.%Y'})
    status = client.get('/labeldesigner/api/printer_status').get_json()
    simulator = next(p for p in status['printers'] if p['path'] == 'simulation')
    assert simulator['settings'] == {'label_size': '62', 'date_format': '%d.%m.%Y'}


def test_the_settings_file_is_not_a_label(tmp_path):
    client = make_client(tmp_path, empty_repo=True, model='QL-800')
    client.post(URL, data={'printer': 'tcp://a', 'label_size': '62'})
    assert client.get('/labeldesigner/api/repository/list').get_json()['files'] == []
    # A label cannot be saved over it, a name loses its leading dot
    r = client.get('/labeldesigner/api/repository/load', query_string={'name': printer_settings.FILE})
    assert r.status_code == 404


def test_settings_are_checked(tmp_path):
    client = make_client(tmp_path, empty_repo=True, model='QL-800')
    for wrong in ({'label_size': 'pt24'}, {'cut': 'sometimes'}, {'quality': 'best'}, {'collate': '2'},
                  {'date_format': '<script>'}, {'colour': 'red'}, {}):
        r = client.post(URL, data={'printer': 'tcp://a', **wrong})
        assert r.status_code == 400, wrong
        assert r.get_json()['message'] in (printer_settings.SETTINGS_MESSAGE, 'The label size 24 mm (TZe tape) cannot be printed on a QL-800')
    assert client.get(URL, query_string={'printer': 'tcp://a'}).get_json() == {}


def test_a_broken_file_is_no_settings(tmp_path):
    client = make_client(tmp_path, empty_repo=True, model='QL-800')
    (tmp_path / 'label_repo' / printer_settings.FILE).write_text('{"printers": [')
    assert client.get(URL, query_string={'printer': 'tcp://a'}).get_json() == {}
    client.post(URL, data={'printer': 'tcp://a', 'cut': 'none'})
    assert json.loads((tmp_path / 'label_repo' / printer_settings.FILE).read_text()) == {'printers': {'tcp://a:9100': {'cut': 'none'}}}


def test_a_usb_printer_is_kept_by_its_serial(monkeypatch):
    monkeypatch.setattr(printer_settings, 'usb_device_id', lambda device: 'MFG:Brother;MDL:QL-800;SN:000F1Z123;')
    assert printer_settings.key('/dev/usb/lp1') == 'usb:QL-800/000F1Z123'
    monkeypatch.setattr(printer_settings, 'usb_device_id', lambda device: 'MFG:Brother;MDL:QL-800;')
    assert printer_settings.key('file:///dev/usb/lp1') == '/dev/usb/lp1'
