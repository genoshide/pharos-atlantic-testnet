import asyncio, aiohttp
from config.config import settings

async def _request(self, url, method, data=None, options={"retries": 1, "isAuth": False}):
    retries = options.get("retries", 1)
    is_auth = options.get("isAuth", False)

    headers = {**self.headers}
    if not is_auth and self.token:
        headers["authorization"] = f"Bearer {self.token}"

    current_retries = 0
    error_message = ""
    error_status = 0

    # Main request #469

    while current_retries <= retries:
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {
                    "method": method.upper(),
                    "url": url,
                    "headers": headers,
                    "proxy": self.proxy if settings["USE_PROXY"] else None,
                }

                if method.lower() != "get" and data:
                    request_kwargs["json"] = data

                async with session.request(**request_kwargs) as resp:
                    response_data = await resp.json()
                    status = resp.status

                    if response_data.get("msg") != "ok":
                        if response_data.get("code") == 100 and "/login" in url:
                            print("Ref code limit reached. Change ref.")
                            await asyncio.sleep(1)
                            exit(0)
                        return {
                            "status": status,
                            "success": False,
                            "data": response_data.get("data"),
                            "error": response_data,
                        }

                    if "data" in response_data:
                        return {
                            "status": status,
                            "success": True,
                            "data": response_data["data"],
                        }

                    return {"status": status, "success": True, "data": response_data}

        except aiohttp.ClientResponseError as error:
            error_message = str(error)
            error_status = error.status
            print(f"Request failed: {url} | {error_message}")

            if error_status == 401:
                token = await self.get_valid_token(force=True)
                if not token:
                    exit(1)
                self.token = token
                return await self._request(url, method, data, options)

            if error_status == 400:
                print(f"Invalid request for {url}. Maybe new update on server.")
                return {
                    "status": error_status,
                    "success": False,
                    "data": None,
                    "error": error_message,
                }

            if error_status == 429:
                print(f"Rate limited: {error_message}, waiting 30s before retrying...")
                await asyncio.sleep(30)

        except Exception as error:
            error_message = str(error)
            error_status = getattr(error, "status", 0)
            print(f"Unexpected error: {url} | {error_message}")
            return {
                "status": error_status,
                "success": False,
                "data": None,
                "error": error_message,
            }

        await asyncio.sleep(settings.get("DELAY_BETWEEN_REQUESTS", 1))
        current_retries += 1

    return {
        "status": error_status,
        "success": False,
        "data": None,
        "error": error_message,
    }