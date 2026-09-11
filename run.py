#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host = app.config['SERVER_HOST'], port = os.environ.get('SERVER_PORT', app.config['SERVER_PORT']))
