"""RunPod cloud adaptor."""

import os
import threading
from typing import Optional

from sky.adaptors import common

_lock = threading.RLock()
_global_module = None
_pending_api_key: Optional[str] = None


def init_api_key(module):
    global _global_module
    with _lock:
        _global_module = module
        api_key = _pending_api_key
        if api_key is None:
            api_key = os.environ.get('RUNPOD_AI_API_KEY')
        if api_key:
            setattr(_global_module, 'api_key', api_key)
        else:
            if hasattr(_global_module, 'api_key'):
                delattr(_global_module, 'api_key')


def update_api_key(api_key: Optional[str]):
    global _pending_api_key
    with _lock:
        _pending_api_key = api_key
        if _global_module is not None:
            if api_key:
                setattr(_global_module, 'api_key', api_key)
            else:
                if hasattr(_global_module, 'api_key'):
                    delattr(_global_module, 'api_key')


runpod = common.LazyImport(
    'runpod',
    import_error_message='Failed to import dependencies for RunPod. '
    'Try running: pip install "skypilot[runpod]"',
    set_loggers=init_api_key)
