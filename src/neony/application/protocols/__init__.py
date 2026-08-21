"""Custom protocol support — Python handlers behind ``neony://<key>/…`` URLs.

Public API::

    from neony.application.protocols import protocol, Request, Response, local_files

Declare handlers with the :func:`protocol` decorator (on plain functions
or methods), then pass them — or instances of classes with decorated
methods — to ``launch(...)`` / ``NeonApplication(...)``::

    launch(page, protocols=[local_files, my_handler])

Must happen before the app runs: webview schemes are registered once at
window creation and cannot be added afterwards.  Build URLs with
:func:`neony.application.urls.local_url` /
:func:`neony.application.urls.protocol_url`.
"""

from neony.application.protocols.base import (
    Request,
    Response,
    collect_protocol_handlers,
    protocol,
)
from neony.application.protocols.files import local_files

__all__ = [
    "Request",
    "Response",
    "collect_protocol_handlers",
    "local_files",
    "protocol",
]
