import json
import aiofiles
from typing import Dict, Any

async def load_config() -> Dict[str, Any]:
    try:
        async with aiofiles.open("config.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {}