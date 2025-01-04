from __future__ import annotations

from collections.abc import Coroutine, MutableMapping
from typing import cast
import asyncio
import base64 as b64
import contextlib
import datetime as dt
import functools as ft
import json
import logging
import pathlib
import warnings

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.orm import DeclarativeBase
import httpx
import sqlalchemy as sa
import tenacity

log = logging.getLogger(__name__)


class _Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""


class CachePolicy:
    """
    Implement a SQLite-based caching policy.

    Write to a filelike database table.

    CREATE TABLE http_cache (
        key            TEXT     PRIMARY KEY,
        status_code    INTEGER,
        headers        BLOB,
        stream         TEXT,
        cache_hits     INTEGER  DEFAULT 0,
        created_at_utc DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """

    # TODO: investigate msgspec.json.encode / .decode for even faster resolution here.

    CACHE_CONTROL_HEADER = "x-cs-tools-cache-control"
    CACHE_BUSTING_HEADER = "x-cs-tools-cache-bust"
    CACHE_FETCHED_HEADER = "x-cs-tools-cache-hit"
    CACHE_RESPONSE_TABLE = sa.Table(
        "http_cache",
        _Base.metadata,
        sa.Column("key", sa.String, primary_key=True),
        sa.Column("status_code", sa.Integer),
        sa.Column("headers", sa.BLOB),
        sa.Column("stream", sa.String),
        sa.Column("cache_hits", sa.Integer, default=0),
        sa.Column("created_at_utc", sa.DateTime, server_default=sa.func.now()),
    )

    def __init__(self, directory: pathlib.Path):
        self._filepath = directory / "http.cache"
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{self._filepath}", future=True)
        self._cnxn: AsyncConnection | None = None
        self._setup_lock = asyncio.Lock()
        self._pending_cache_tasks: set[asyncio.Task] = set()

    def _background_task(self, coro: Coroutine) -> None:
        """Safely run a task in the background."""
        task = asyncio.create_task(coro)
        task.add_done_callback(lambda t: self._pending_cache_tasks.remove(t))
        self._pending_cache_tasks.add(task)

    @classmethod
    def mark_cacheable(cls, fn):
        """Mark an HTTPX endpoint as cacheable by injecting the cache control header."""

        @ft.wraps(fn)
        def wrapper(self, *a, headers: httpx._types.HeaderTypes | None = None, **kw) -> httpx.Response:
            headers = cast(MutableMapping[str, str], headers)

            if headers is None:
                headers = {}

            headers[cls.CACHE_CONTROL_HEADER] = "true"
            return fn(self, *a, headers=headers, **kw)

        return wrapper

    async def _setup_database(self) -> None:
        """Ensure the database cache is set up."""
        if self._cnxn is not None:
            return

        async with self._setup_lock:
            if self._cnxn is not None:
                return

            warnings.filterwarnings(
                "ignore",
                message="transaction already deassociated from connection",
                category=sa.exc.SAWarning,
            )

            self._cnxn = await self._engine.connect()

            await self._cnxn.run_sync(_Base.metadata.create_all)

    async def aclose(self) -> None:
        """Close the database."""
        if self._pending_cache_tasks:
            with contextlib.suppress(AssertionError):
                await asyncio.gather(*self._pending_cache_tasks)

        if self._cnxn is not None:
            await self._cnxn.aclose()

    async def _sql_select(self, *, key: str) -> sa.Row | None:
        """Maybe-retrieve a response from the cache."""
        assert self._cnxn is not None, "Caching database is not setup."

        query = sa.select(CachePolicy.CACHE_RESPONSE_TABLE).where(CachePolicy.CACHE_RESPONSE_TABLE.c.key == key)

        result = await self._cnxn.execute(query)
        return result.fetchone()

    async def _sql_delete(self, *, key: str) -> None:
        """Remove a response from the cache."""
        assert self._cnxn is not None, "Caching database is not setup."

        query = sa.delete(CachePolicy.CACHE_RESPONSE_TABLE).where(CachePolicy.CACHE_RESPONSE_TABLE.c.key == key)

        await self._cnxn.execute(query)

    async def _sql_insert(self, *, key: str, r: httpx.Response, hits: int | None = None) -> None:
        """Add or Update a response to the cache."""
        assert self._cnxn is not None, "Caching database is not setup."

        s = r.status_code
        h = json.dumps([(k, v) for k, v in r.headers.raw], default=str).encode("utf-8")
        d = b64.b64encode(r.content).decode("ascii")

        # INSERT ... VALUES
        query = insert(CachePolicy.CACHE_RESPONSE_TABLE).values(key=key, status_code=s, headers=h, stream=d)

        # ON CONFLICT DO UPDATE
        data_to_update = {"cache_hits": hits} if hits is not None else {"status_code": s, "headers": h, "stream": d}  # type: ignore[dict-item]
        query = query.on_conflict_do_update(index_elements=["key"], set_=data_to_update)

        await self._cnxn.execute(query)
        await self._cnxn.commit()

    async def _cache_lookup(self, *, key: str) -> httpx.Response | None:
        """Retrieve the response from cache."""
        assert self._cnxn is not None, "Caching database is not setup."

        if not (cached := await self._sql_select(key=key)):
            return None

        response = httpx.Response(
            status_code=cached.status_code,
            headers=json.loads(cached.headers),
            content=b64.b64decode(cached.stream.encode("ascii")),
        )

        # Update the cache metadata
        self._background_task(coro=self._sql_insert(key=key, r=response, hits=cached.cache_hits + 1))

        return response

    async def build_cache_key(self, request: httpx.Request) -> str:
        """Define a unique key to identify the request."""
        # READ THE REQUEST BODY SO WE CAN ACCURATELY CACHE ITS REPRESENTATION.
        body = await request.aread()

        # NORMALIZE THE URL IN CASE OF INTERESTING CHARACTERS.
        p = f":{request.url.port}" if request.url.port else ""
        u = f"{request.url.raw_host.decode('utf-8')}{p}/{request.url.raw_path.decode('utf-8')}"

        # ADD THE PARAMS AND DATA AS QUERY STRING.
        q = ""

        if request.url.query:
            q += f"::params::{request.url.query.decode('utf-8')}"

        if body:
            q += f"::data::{body.decode('utf-8')}"

        return f"{u}?{q}"

    def should_cache(self, request: httpx.Request, response: httpx.Response) -> bool:
        """Determine if the response should be cached."""
        return CachePolicy.CACHE_CONTROL_HEADER in request.headers and response.status_code < 300

    async def check(self, request: httpx.Request) -> httpx.Response | None:
        """Maybe fetch the response from the cache."""
        should_cache = CachePolicy.CACHE_CONTROL_HEADER in request.headers
        busted_cache = CachePolicy.CACHE_BUSTING_HEADER in request.headers

        if not should_cache:
            return None

        await self._setup_database()

        sk_cache_key = await self.build_cache_key(request)

        if busted_cache:
            self._background_task(coro=self._sql_delete(key=sk_cache_key))

        if (r := await self._cache_lookup(key=sk_cache_key)) is not None:
            # ATTACH THE REQUEST TO THE CACHED RESPONSE
            r.request = request

            # ADD THE CACHE HIT HEADER
            r.headers[CachePolicy.CACHE_FETCHED_HEADER] = "true"
            return r

        return None

    async def store(self, request: httpx.Request, response: httpx.Response) -> None:
        """Store the response in the cache."""
        sk_cache_key = await self.build_cache_key(request)

        # READ THE BODY SO WE CAN CACHE IT
        await response.aread()

        # ADD THE REQUEST TO THE RESPONSE
        response.request = request

        self._background_task(coro=self._sql_insert(key=sk_cache_key, r=response))

    async def expire(self, request: httpx.Request) -> None:
        """Remove the response from the cache."""
        sk_cache_key = await self.build_cache_key(request)
        await self._sql_delete(key=sk_cache_key)

    async def clear(self) -> None:
        """Remove all responses from the cache."""
        if self._cnxn is None:
            log.warning("Cache is not yet set up.")
            return

        await self._cnxn.run_sync(_Base.metadata.drop_all)
        await self._cnxn.run_sync(_Base.metadata.create_all)


class CachedRetryTransport(httpx.AsyncBaseTransport):
    """Implements a retry policy with caching on every HTTP request."""

    def __init__(
        self,
        cache_policy: CachePolicy | None = None,
        max_concurrent_requests: int = 1,
        retry_policy: tenacity.AsyncRetrying | None = None,
    ):
        self._wrapper = httpx.AsyncHTTPTransport()
        self.cache = cache_policy
        self.rate_limit = asyncio.Semaphore(value=max_concurrent_requests)
        self.retrier = retry_policy or tenacity.AsyncRetrying(stop=tenacity.stop_after_attempt(1))

    @property
    def max_concurrency(self) -> int:
        """Get the allowed maximum number of concurrent requests."""
        return self.rate_limit._value

    async def _handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Ensure request is injected on exception."""
        with httpx._exceptions.request_context(request=request):
            r = await self._wrapper.handle_async_request(request=request)

        return r

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        UTC_NOW = ft.partial(dt.datetime.now, tz=dt.timezone.utc)

        # SET THE REQUEST DISPATCH TIME
        request.headers["x-cs-tools-request-dispatch-time-utc"] = UTC_NOW().isoformat()

        # CACHE HITS SHOULD NOT AFFECT RATE LIMITS
        if self.cache is not None and (cached_response := await self.cache.check(request=request)):
            # SET THE EFFECTIVE RESPONSE TIME
            cached_response.headers["x-cs-tools-response-receive-time-utc"] = UTC_NOW().isoformat()

            return cached_response

        # RATE LIMITING OUTSIDE OF RETRYING SO WE EFFECTIVELY IMPLEMENT BACKPRESSURE
        async with self.rate_limit:
            # OVERRIDE THE REQUEST DISPATCH TIME IN CASE WE'VE BEEN WAITING
            request.headers["x-cs-tools-request-dispatch-time-utc"] = UTC_NOW().isoformat()

            try:
                response: httpx.Response = await self.retrier(self._handle_async_request, request=request)
            except tenacity.RetryError as error:
                raise error from None
            except Exception as error:
                raise error from None

        # SET THE EFFECTIVE RESPONSE TIME
        response.headers["x-cs-tools-response-receive-time-utc"] = UTC_NOW().isoformat()

        # CHECK IF WE SHOULD CACHE THE RESPONSE
        if self.cache is not None and self.cache.should_cache(request=request, response=response):
            await self.cache.store(request=request, response=response)

        return response

    async def aclose(self) -> None:
        """Close the transport."""
        await self._wrapper.aclose()

        if self.cache is not None:
            await self.cache.aclose()
