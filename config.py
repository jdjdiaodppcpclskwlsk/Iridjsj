import json
import aiofiles
import os
from typing import Dict, Any

async def load_config() -> Dict[str, Any]:
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        print(f"Loading config from: {config_path}")
        
        async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
            content = await f.read()
            print(f"Config file size: {len(content)} bytes")
            return json.loads(content)
    except FileNotFoundError:
        print("ERROR: config.json not found!")
        return {}
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config.json: {e}")
        return {}
    except Exception as e:
        print(f"ERROR loading config: {e}")
        return {}