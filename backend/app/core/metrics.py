"""
Request metrics collection for admin dashboard.

Provides lightweight request tracking without heavy infrastructure:
- In-memory storage with rolling window
- Route-level statistics
- Status code distribution
- Average latency tracking
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RequestMetric:
    """Single request metric entry."""
    timestamp: datetime
    path: str
    method: str
    status_code: int
    latency_ms: float


@dataclass  
class MetricsStore:
    """Thread-safe metrics storage with rolling window."""
    
    # Configuration
    max_entries: int = 10000  # Max entries to keep
    window_hours: int = 24    # Rolling window size
    
    # Storage
    _metrics: List[RequestMetric] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)
    
    def record(self, metric: RequestMetric) -> None:
        """Record a new metric."""
        with self._lock:
            self._metrics.append(metric)
            self._cleanup()
    
    def _cleanup(self) -> None:
        """Remove old entries outside the window."""
        cutoff = datetime.utcnow() - timedelta(hours=self.window_hours)
        
        # Remove old entries
        self._metrics = [m for m in self._metrics if m.timestamp >= cutoff]
        
        # Trim if too many
        if len(self._metrics) > self.max_entries:
            self._metrics = self._metrics[-self.max_entries:]
    
    def get_stats(self, hours: int = 24) -> dict:
        """
        Get aggregated statistics for the last N hours.
        
        Args:
            hours: Number of hours to aggregate
            
        Returns:
            Dictionary with traffic statistics
        """
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            recent = [m for m in self._metrics if m.timestamp >= cutoff]
        
        if not recent:
            return {
                "period_hours": hours,
                "request_count_total": 0,
                "requests_by_route": {},
                "status_code_counts": {},
                "avg_latency_ms": 0,
                "p95_latency_ms": 0,
                "requests_per_minute": 0,
            }
        
        # Aggregate by route
        route_counts: Dict[str, int] = defaultdict(int)
        for m in recent:
            route_key = f"{m.method} {m.path}"
            route_counts[route_key] += 1
        
        # Top 20 routes
        top_routes = dict(sorted(
            route_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20])
        
        # Status code distribution
        status_counts: Dict[str, int] = defaultdict(int)
        for m in recent:
            status_group = f"{m.status_code // 100}xx"
            status_counts[status_group] += 1
        
        # Latency stats
        latencies = [m.latency_ms for m in recent]
        avg_latency = sum(latencies) / len(latencies)
        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_idx] if sorted_latencies else 0
        
        # Requests per minute
        if recent:
            time_range = (recent[-1].timestamp - recent[0].timestamp).total_seconds()
            if time_range > 0:
                rpm = len(recent) / (time_range / 60)
            else:
                rpm = len(recent)
        else:
            rpm = 0
        
        return {
            "period_hours": hours,
            "request_count_total": len(recent),
            "requests_by_route": top_routes,
            "status_code_counts": dict(status_counts),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "requests_per_minute": round(rpm, 2),
        }


# Global metrics store instance
metrics_store = MetricsStore()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics."""
    
    # Paths to exclude from metrics
    EXCLUDE_PATHS = {"/api/health", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip excluded paths
        path = request.url.path
        if path in self.EXCLUDE_PATHS:
            return await call_next(request)
        
        # Normalize path (replace UUIDs with placeholder)
        normalized_path = self._normalize_path(path)
        
        # Record timing
        start_time = time.time()
        response = await call_next(request)
        latency_ms = (time.time() - start_time) * 1000
        
        # Record metric
        metric = RequestMetric(
            timestamp=datetime.utcnow(),
            path=normalized_path,
            method=request.method,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        metrics_store.record(metric)
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing UUIDs and IDs with placeholders.
        
        This prevents route explosion in metrics.
        """
        import re
        
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        return path


def get_traffic_stats(hours: int = 24) -> dict:
    """Get traffic statistics for the specified period."""
    return metrics_store.get_stats(hours)
