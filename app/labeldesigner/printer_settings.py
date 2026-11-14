"""The settings made in the printer settings of the label designer: the
label size set by hand, the cutting, the quality, collating and the date
format. They are kept on the server, so that every browser, the API and the
MCP tools use the same. The roll is in the printer, its settings belong to
it rather than to a browser.

They are kept in one file in the folder of the labels, the folder a Docker
setup keeps. A change names only the settings it changes, two browsers
changing different settings at the same time keep both."""
import json
import re

from .drivers.devices import lock_key, usb_device_id
from .label_names import check_cut, check_label_size

# In the folder of the labels, hidden: saved labels never start with a dot
FILE = '.printers.json'
# The same for every printer
COMMON = ('quality', 'collate', 'date_format')
# Of each printer
OWN = ('label_size', 'cut', 'half_cut', 'chain', 'leaves_first')
QUALITIES = ('quality', 'high', 'fast')
CUTS = ('each', 'last', 'none')
# strftime codes of a date and what goes between them, e.g. %d.%m.%Y
DATE_FORMAT = re.compile(r'(%[YymdbBe]|[ ./-]){1,10}')
# Printers come and go, a few hundred are a lot already
MAX_PRINTERS = 200

SETTINGS_MESSAGE = ('settings are label_size, cut (each, last or none), half_cut and chain (0 or 1), '
                    'leaves_first (top or bottom) of a printer, '
                    'quality (quality, high or fast), collate (0 or 1) and date_format (e.g. %d.%m.%Y), '
                    'an empty value removes one')
TOO_MANY_PRINTERS = f'Settings are kept for at most {MAX_PRINTERS} printers'


def key(device: str) -> str:
    """The printer a setting belongs to: on USB by its serial number where
    its device ID tells one, as /dev/usb/lp<N> changes when printers are
    plugged in another order, else by its device."""
    fields = dict(field.split(':', 1) for field in usb_device_id(device).split(';') if ':' in field)
    serial = (fields.get('SN') or fields.get('SERN') or '').strip()
    model = (fields.get('MDL') or fields.get('MODEL') or '').strip()
    return f'usb:{model}/{serial}' if serial else lock_key(device)


def parsed(content: str) -> dict:
    """The settings kept in the file, nothing of a broken one."""
    try:
        data = json.loads(content)
    except ValueError:
        return {'printers': {}}
    if not isinstance(data, dict) or not isinstance(data.get('printers'), dict):
        return {'printers': {}}
    return data


def of_printer(data: dict, device: str) -> dict:
    """The settings of a printer, the common ones with its own."""
    own = data['printers'].get(key(device))
    return {**{name: data[name] for name in COMMON if name in data},
            **{name: own[name] for name in OWN if isinstance(own, dict) and name in own}}


def checked(changes: dict, model: str) -> dict:
    """The changes as kept, ValueError for one the printer model cannot take."""
    if not changes or any(name not in COMMON + OWN or not isinstance(value, str) for name, value in changes.items()):
        raise ValueError(SETTINGS_MESSAGE)
    for name, value in changes.items():
        if not value:
            continue
        if name == 'label_size':
            check_label_size(value, model)
        elif name == 'cut':
            if value not in CUTS:
                raise ValueError(SETTINGS_MESSAGE)
            check_cut(value, model)
        elif name in ('half_cut', 'chain', 'collate'):
            if value not in ('0', '1'):
                raise ValueError(SETTINGS_MESSAGE)
        elif name == 'leaves_first':
            if value not in ('top', 'bottom'):
                raise ValueError(SETTINGS_MESSAGE)
        elif name == 'quality':
            if value not in QUALITIES:
                raise ValueError(SETTINGS_MESSAGE)
        elif not DATE_FORMAT.fullmatch(value):
            raise ValueError(SETTINGS_MESSAGE)
    return changes


def changed(data: dict, device: str, changes: dict) -> dict:
    """data with the checked changes made, an empty value removes one."""
    printer = key(device)
    own = data['printers'].get(printer)
    own = dict(own) if isinstance(own, dict) else {}
    for name, value in changes.items():
        target = data if name in COMMON else own
        if value:
            target[name] = value
        else:
            target.pop(name, None)
    if own:
        data['printers'][printer] = own
    else:
        data['printers'].pop(printer, None)
    if len(data['printers']) > MAX_PRINTERS:
        raise ValueError(TOO_MANY_PRINTERS)
    return data
