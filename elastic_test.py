import asyncio
from search_users_tool import search_users
import json

from user_type_enum import UserType


async def test_search_users():
    result = await search_users(name="Jimmi Thakkar",contact="9586345111",email="licensing", userType=UserType.TECHNICIAN)
    print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_search_users())
